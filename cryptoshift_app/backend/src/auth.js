// Accounts, sessions and role-based access control. No external dependencies:
// - passwords: scrypt (N=2^15, r=8, p=3, 32-byte salt), one of the OWASP Password Storage
//   Cheat Sheet's recommended scrypt configurations; compared with timingSafeEqual.
// - sessions: 256-bit random token in an HttpOnly, SameSite=Strict cookie. Only its SHA-256
//   is kept server side. Each session has its own CSRF token, required on every POST.
// - first admin: created through a one-time setup token printed on the server console.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { promisify } from "node:util";

const scrypt = promisify(crypto.scrypt);
const SCRYPT = { N: 2 ** 15, r: 8, p: 3, maxmem: 64 * 1024 * 1024 };
const KEYLEN = 32;

export const ROLES = ["viewer", "engineer", "reviewer", "admin"];
const RANK = Object.fromEntries(ROLES.map((r, i) => [r, i]));
export const atLeast = (user, role) => Boolean(user) && RANK[user.role] >= RANK[role];

export const PASSWORD_MIN = 15; // NIST SP 800-63B: 15 characters for single-factor passwords
const PASSWORD_MAX = 256;
const SESSION_TTL_MS = 8 * 60 * 60 * 1000;
const IDLE_TTL_MS = 60 * 60 * 1000;
const MAX_FAILURES = 5;
const LOCK_MS = 15 * 60 * 1000;

export async function hashPassword(password) {
  const salt = crypto.randomBytes(32);
  const hash = await scrypt(password.normalize("NFKC"), salt, KEYLEN, SCRYPT);
  return `scrypt$${SCRYPT.N}$${SCRYPT.r}$${SCRYPT.p}$${salt.toString("base64")}$${hash.toString("base64")}`;
}

export async function verifyPassword(password, stored) {
  const [scheme, N, r, p, salt, hash] = String(stored).split("$");
  if (scheme !== "scrypt") return false;
  const expected = Buffer.from(hash, "base64");
  const actual = await scrypt(password.normalize("NFKC"), Buffer.from(salt, "base64"), expected.length, { N: Number(N), r: Number(r), p: Number(p), maxmem: SCRYPT.maxmem });
  return crypto.timingSafeEqual(actual, expected);
}

export function passwordProblem(password, username = "") {
  if (typeof password !== "string") return "Password is required";
  if ([...password].length < PASSWORD_MIN) return `Use at least ${PASSWORD_MIN} characters (a few unrelated words work well)`;
  if (password.length > PASSWORD_MAX) return `Use at most ${PASSWORD_MAX} characters`;
  if (username && password.toLowerCase().includes(username.toLowerCase())) return "Password must not contain the username";
  if (/^(.)\1+$/.test(password)) return "Password must not be one repeated character";
  return null;
}

const USERNAME = /^[a-z0-9][a-z0-9._-]{2,31}$/;
const sha256 = (s) => crypto.createHash("sha256").update(s).digest("hex");
const safeEqual = (a, b) => {
  const x = Buffer.from(String(a));
  const y = Buffer.from(String(b));
  return x.length === y.length && crypto.timingSafeEqual(x, y);
};

export function createAuth(dataDir, { log = console.log } = {}) {
  const usersFile = path.join(dataDir, "users.json");
  const setupFile = path.join(dataDir, "setup-token");
  fs.mkdirSync(dataDir, { recursive: true });
  let users = fs.existsSync(usersFile) ? JSON.parse(fs.readFileSync(usersFile, "utf8")) : [];
  const sessions = new Map(); // sha256(token) -> session
  const failures = new Map(); // key -> { count, until }
  let setupToken = null;

  const persist = () => fs.writeFileSync(usersFile, JSON.stringify(users, null, 2), { mode: 0o600 });
  const publicUser = (u) => ({ id: u.id, username: u.username, displayName: u.displayName, role: u.role, disabled: Boolean(u.disabled), createdAt: u.createdAt, lastLoginAt: u.lastLoginAt ?? null, mustChangePassword: Boolean(u.mustChangePassword) });

  function ensureSetupToken() {
    if (users.length) {
      fs.rmSync(setupFile, { force: true });
      return null;
    }
    const fromEnv = process.env.CRYPTOSHIFT_SETUP_TOKEN;
    if (fromEnv && fromEnv.length >= 16) {
      setupToken = fromEnv; // hosted deployments: set it as a secret, use it once, then delete it
      log("CryptoShift has no accounts yet: create the first administrator with the CRYPTOSHIFT_SETUP_TOKEN secret.");
      return setupToken;
    }
    setupToken = crypto.randomBytes(18).toString("base64url");
    fs.writeFileSync(setupFile, setupToken + "\n", { mode: 0o600 });
    log(`\n  CryptoShift has no accounts yet. Create the first administrator in the browser with this one-time setup code:\n\n      ${setupToken}\n\n  (also saved to ${setupFile}, readable only by you)\n`);
    return setupToken;
  }

  async function addUser({ username, displayName, password, role }, { mustChangePassword = false } = {}) {
    username = String(username ?? "").trim().toLowerCase();
    displayName = String(displayName ?? "").trim().slice(0, 80) || username;
    if (!USERNAME.test(username)) return { error: 400, message: "Username: 3–32 characters, lowercase letters, digits, dot, dash or underscore" };
    if (!ROLES.includes(role)) return { error: 400, message: "Unknown role" };
    if (users.some((u) => u.username === username)) return { error: 409, message: "That username is taken" };
    const problem = passwordProblem(password, username);
    if (problem) return { error: 400, message: problem };
    const user = { id: crypto.randomUUID(), username, displayName, role, passwordHash: await hashPassword(password), createdAt: new Date().toISOString(), mustChangePassword };
    users.push(user);
    persist();
    return { user: publicUser(user) };
  }

  async function setup({ token, username, displayName, password }) {
    if (users.length) return { error: 409, message: "Setup is already complete" };
    if (!setupToken || !safeEqual(String(token ?? "").trim(), setupToken)) return { error: 403, message: "Setup code is not valid. Copy it from the server console." };
    const result = await addUser({ username, displayName, password, role: "admin" });
    if (result.user) {
      setupToken = null;
      fs.rmSync(setupFile, { force: true });
    }
    return result;
  }

  function newSession(user) {
    const token = crypto.randomBytes(32).toString("base64url");
    const now = Date.now();
    const session = { userId: user.id, csrf: crypto.randomBytes(32).toString("base64url"), createdAt: now, lastSeen: now };
    sessions.set(sha256(token), session);
    return { token, session };
  }

  async function login({ username, password }, ip = "") {
    username = String(username ?? "").trim().toLowerCase();
    const key = `${ip}|${username}`;
    const f = failures.get(key);
    if (f?.until && f.until > Date.now()) return { error: 429, message: `Too many failed attempts. Try again in ${Math.ceil((f.until - Date.now()) / 60000)} minutes.` };
    const user = users.find((u) => u.username === username);
    // Hash even for unknown users so response time does not reveal which usernames exist.
    const ok = user ? await verifyPassword(String(password ?? ""), user.passwordHash) : (await hashPassword("timing-equaliser-value"), false);
    if (!ok || user.disabled) {
      const count = (f?.until && f.until <= Date.now() ? 0 : f?.count ?? 0) + 1;
      failures.set(key, { count, until: count >= MAX_FAILURES ? Date.now() + LOCK_MS : null });
      return { error: 401, message: "Username or password is incorrect" };
    }
    failures.delete(key);
    user.lastLoginAt = new Date().toISOString();
    persist();
    const { token, session } = newSession(user);
    return { token, csrf: session.csrf, user: publicUser(user) };
  }

  function resolve(token) {
    if (!token) return null;
    const id = sha256(token);
    const session = sessions.get(id);
    if (!session) return null;
    const now = Date.now();
    const user = users.find((u) => u.id === session.userId);
    if (!user || user.disabled || now - session.createdAt > SESSION_TTL_MS || now - session.lastSeen > IDLE_TTL_MS) {
      sessions.delete(id);
      return null;
    }
    session.lastSeen = now;
    return { user: publicUser(user), csrf: session.csrf, sessionId: id };
  }

  const logout = (token) => token && sessions.delete(sha256(token));
  const dropSessionsOf = (userId, keep) => {
    for (const [id, s] of sessions) if (s.userId === userId && id !== keep) sessions.delete(id);
  };

  async function changePassword(userId, { current, next }, sessionId) {
    const user = users.find((u) => u.id === userId);
    if (!user) return { error: 404, message: "Account not found" };
    if (!(await verifyPassword(String(current ?? ""), user.passwordHash))) return { error: 403, message: "Current password is incorrect" };
    const problem = passwordProblem(next, user.username);
    if (problem) return { error: 400, message: problem };
    user.passwordHash = await hashPassword(next);
    user.mustChangePassword = false;
    persist();
    dropSessionsOf(userId, sessionId); // sign out every other device
    return { user: publicUser(user) };
  }

  function updateUser(actorId, userId, { role, disabled }) {
    const user = users.find((u) => u.id === userId);
    if (!user) return { error: 404, message: "Account not found" };
    if (role !== undefined && !ROLES.includes(role)) return { error: 400, message: "Unknown role" };
    const admins = users.filter((u) => u.role === "admin" && !u.disabled);
    const losesAdmin = user.role === "admin" && !user.disabled && ((role !== undefined && role !== "admin") || disabled === true);
    if (losesAdmin && admins.length === 1) return { error: 409, message: "At least one active administrator must remain" };
    if (userId === actorId && disabled === true) return { error: 409, message: "You cannot disable your own account" };
    if (role !== undefined) user.role = role;
    if (disabled !== undefined) user.disabled = Boolean(disabled);
    persist();
    if (user.disabled || role !== undefined) dropSessionsOf(userId);
    return { user: publicUser(user) };
  }

  return {
    ensureSetupToken,
    setupRequired: () => users.length === 0,
    setup,
    addUser,
    login,
    resolve,
    logout,
    changePassword,
    updateUser,
    listUsers: () => users.map(publicUser),
    reset: () => {
      users = [];
      sessions.clear();
      failures.clear();
      fs.rmSync(usersFile, { force: true });
    },
  };
}
