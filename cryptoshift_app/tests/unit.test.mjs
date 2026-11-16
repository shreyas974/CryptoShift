// Unit tests for the security primitives. Run: node --test tests/unit.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { openAuditLog } from "../backend/src/auditlog.js";
import { hashPassword, verifyPassword, passwordProblem, createAuth, atLeast } from "../backend/src/auth.js";
import { deadlineFor } from "../backend/src/standards.js";

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "cs-unit-"));

test("scrypt known-answer vector (RFC 7914 §12, N=16 r=1 p=1)", () => {
  // Confirms the KDF primitive the password hashing relies on matches the published vector.
  const out = crypto.scryptSync("", "", 64, { N: 16, r: 1, p: 1 }).toString("hex");
  assert.equal(out, "77d6576238657b203b19ca42c18a0497f16b4844e3074ae8dfdffa3fede21442fcd0069ded0948f8326a753a0fc81f17e8d3e0fb2e0d3628cf35e20c38d18906");
});

test("HMAC-SHA256 known-answer vector (RFC 4231 test case 2)", () => {
  const mac = crypto.createHmac("sha256", "Jefe").update("what do ya want for nothing?").digest("hex");
  assert.equal(mac, "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843");
});

test("password hashes verify, are salted, and reject wrong passwords", async () => {
  const a = await hashPassword("correct horse battery staple");
  const b = await hashPassword("correct horse battery staple");
  assert.notEqual(a, b, "same password must give different hashes (random salt)");
  assert.match(a, /^scrypt\$32768\$8\$3\$/);
  assert.equal(await verifyPassword("correct horse battery staple", a), true);
  assert.equal(await verifyPassword("correct horse battery stapler", a), false);
  assert.equal(await verifyPassword("anything", "md5$abc"), false, "unknown schemes never verify");
});

test("password policy", () => {
  assert.ok(passwordProblem("short"));
  assert.ok(passwordProblem("aaaaaaaaaaaaaaaaaaaa"));
  assert.ok(passwordProblem("my name is alice and more", "alice"));
  assert.equal(passwordProblem("four random words here"), null);
});

test("role ranking", () => {
  assert.equal(atLeast({ role: "admin" }, "reviewer"), true);
  assert.equal(atLeast({ role: "engineer" }, "reviewer"), false);
  assert.equal(atLeast(null, "viewer"), false);
});

test("audit chain verifies and detects edits, deletions, reordering and forged MACs", () => {
  const dir = tmp();
  const log = openAuditLog(dir);
  for (let i = 0; i < 5; i++) log.append("act", `entry ${i}`, "alice");
  assert.equal(log.verify().ok, true);
  const file = path.join(dir, "audit.log");
  const original = fs.readFileSync(file, "utf8").trim().split("\n");
  const variants = {
    edit: original.map((l, i) => (i === 2 ? l.replace("entry 2", "entry X") : l)),
    delete: original.filter((_, i) => i !== 2),
    reorder: [original[0], original[2], original[1], ...original.slice(3)],
    forge: original.map((l, i) => (i === 3 ? JSON.stringify({ ...JSON.parse(l), detail: "forged", mac: crypto.createHash("sha256").update("x").digest("hex") }) : l)),
    truncateTail: original.slice(0, 4), // truncation of the newest entries is NOT detectable by a chain alone
  };
  for (const [name, lines] of Object.entries(variants)) {
    fs.writeFileSync(file, lines.join("\n") + "\n");
    const v = openAuditLog(dir).verify();
    if (name === "truncateTail") assert.equal(v.ok, true, "documented limitation: compare the head hash with an external copy");
    else assert.equal(v.ok, false, name);
  }
  fs.rmSync(dir, { recursive: true });
});

test("audit chain is keyed: recomputing hashes without the key does not hide an edit", () => {
  const dir = tmp();
  const log = openAuditLog(dir);
  log.append("a", "1", "x");
  log.append("b", "2", "x");
  const file = path.join(dir, "audit.log");
  const [l0, l1] = fs.readFileSync(file, "utf8").trim().split("\n").map((l) => JSON.parse(l));
  l0.detail = "changed";
  l0.mac = crypto.createHash("sha256").update(JSON.stringify(l0)).digest("hex"); // attacker without the key
  l1.prev = l0.mac;
  fs.writeFileSync(file, [l0, l1].map((x) => JSON.stringify(x)).join("\n") + "\n");
  assert.equal(openAuditLog(dir).verify().ok, false);
  fs.rmSync(dir, { recursive: true });
});

test("sessions: login, CSRF token per session, logout, disabled accounts", async () => {
  const dir = tmp();
  process.env.CRYPTOSHIFT_SETUP_TOKEN = "unit-test-setup-token-123";
  const auth = createAuth(dir, { log: () => {} });
  auth.ensureSetupToken();
  assert.equal((await auth.setup({ token: "unit-test-setup-token-123", username: "root", password: "a long admin passphrase" })).user.role, "admin");
  await auth.addUser({ username: "bob", password: "a long passphrase for him", role: "engineer" });
  const s1 = await auth.login({ username: "bob", password: "a long passphrase for him" });
  const s2 = await auth.login({ username: "bob", password: "a long passphrase for him" });
  assert.notEqual(s1.csrf, s2.csrf);
  assert.equal(auth.resolve(s1.token).user.username, "bob");
  assert.equal(auth.resolve("forged-token"), null);
  auth.logout(s1.token);
  assert.equal(auth.resolve(s1.token), null);
  const bob = auth.listUsers().find((u) => u.username === "bob");
  const root = auth.listUsers().find((u) => u.username === "root");
  auth.updateUser(root.id, bob.id, { disabled: true });
  assert.equal(auth.resolve(s2.token), null, "disabling an account ends its sessions");
  assert.equal(auth.updateUser(root.id, root.id, { role: "viewer" }).error, 409, "the last admin cannot be demoted");
  assert.ok(!JSON.stringify(auth.listUsers()).includes("scrypt$"), "password hashes never leave the module");
  const mode = fs.statSync(path.join(dir, "users.json")).mode & 0o777;
  if (process.platform !== "win32") assert.equal(mode, 0o600);
  delete process.env.CRYPTOSHIFT_SETUP_TOKEN;
  fs.rmSync(dir, { recursive: true });
});

test("NIST transition deadlines", () => {
  const at = new Date("2026-06-01T00:00:00Z");
  assert.deepEqual([deadlineFor({ family: "RSA" }, at).deprecatedAfter, deadlineFor({ family: "RSA" }, at).disallowedAfter, deadlineFor({ family: "RSA" }, at).yearsLeft], [2030, 2035, 9]);
  assert.equal(deadlineFor({ family: "ECC" }, new Date("2031-01-01Z")).status, "deprecated");
  assert.equal(deadlineFor({ family: "ECC" }, new Date("2035-06-01Z")).status, "disallowed");
  assert.equal(deadlineFor({ family: "AES" }, at).status, "none");
});
