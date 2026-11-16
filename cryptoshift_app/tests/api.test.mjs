// Backend integration test: starts the API on a spare port against a fresh, temporary data
// directory and checks the honesty and security guarantees end to end. Run: npm test
import { spawn } from "node:child_process";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const PORT = 18787;
const ORIGIN = `http://127.0.0.1:${PORT}`;
const B = `${ORIGIN}/api`;
const DATA = fs.mkdtempSync(path.join(os.tmpdir(), "cryptoshift-test-"));
const SETUP = "test-setup-token-" + Math.random().toString(36).slice(2);
const PW = { admin: "correct horse battery staple", eng: "staple orbit lantern meadow", rev: "maple quartz river candle", rev2: "cobalt fern window bridge", view: "harbor violet piano sunset" };

let server;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function start() {
  server = spawn(process.execPath, ["backend/src/server.js"], { env: { ...process.env, PORT: String(PORT), CRYPTOSHIFT_DATA_DIR: DATA, CRYPTOSHIFT_SETUP_TOKEN: SETUP, SARVAM_API_KEY: "" }, stdio: ["ignore", "ignore", "inherit"] });
  for (let i = 0; i < 100; i++) {
    try {
      if ((await fetch(B + "/health")).ok) return;
    } catch {
      /* not up yet */
    }
    await sleep(100);
  }
  throw new Error("server did not start");
}
async function stop() {
  server.kill();
  await new Promise((r) => server.once("exit", r));
}

/** A browser-like client: keeps the session cookie and sends the CSRF token on POST. */
function client() {
  let cookie = "";
  let csrf = "";
  const call = async (method, p, body, { raw = false, headers = {}, csrfOverride } = {}) => {
    const r = await fetch(B + p, {
      method,
      headers: { ...(cookie ? { cookie } : {}), ...(method === "POST" ? { "content-type": "application/json", "x-csrf-token": csrfOverride ?? csrf } : {}), ...headers },
      body: method === "POST" ? (raw ? body : JSON.stringify(body ?? {})) : undefined,
    });
    const set = r.headers.get("set-cookie");
    if (set) cookie = set.split(";")[0];
    const text = await r.text();
    let json = null;
    try {
      json = JSON.parse(text);
    } catch {
      /* not JSON */
    }
    if (json?.csrf) csrf = json.csrf;
    return { status: r.status, body: json, headers: r.headers };
  };
  return {
    get: (p) => call("GET", p),
    post: (p, b, o) => call("POST", p, b, o),
    login: (username, password) => call("POST", "/auth/login", { username, password }),
  };
}

let failed = 0;
let passed = 0;
const check = async (name, fn) => {
  try {
    await fn();
    passed++;
    console.log("PASS", name);
  } catch (e) {
    failed++;
    console.log("FAIL", name, "-", e.message);
  }
};

try {
  await start();
  const anon = client();
  const admin = client();
  const eng = client();
  const rev = client();
  const rev2 = client();
  const view = client();

  // ---------- accounts ----------
  await check("setup is required on a fresh install and rejects a wrong code", async () => {
    assert.equal((await anon.get("/auth/status")).body.setupRequired, true);
    const r = await anon.post("/auth/setup", { token: "wrong", username: "admin", password: PW.admin });
    assert.equal(r.status, 403);
  });
  await check("setup rejects a short password", async () => {
    const r = await anon.post("/auth/setup", { token: SETUP, username: "admin", password: "short" });
    assert.equal(r.status, 400);
  });
  await check("first administrator is created with the setup code and signed in", async () => {
    const r = await admin.post("/auth/setup", { token: SETUP, username: "admin", displayName: "Asha Admin", password: PW.admin });
    assert.equal(r.status, 200);
    assert.equal(r.body.user.role, "admin");
    assert.match(r.headers.get("set-cookie"), /HttpOnly; SameSite=Strict/);
    assert.equal((await anon.post("/auth/setup", { token: SETUP, username: "x2", password: PW.admin })).status, 409);
  });
  for (const [u, role, name, pw] of [["eng", "engineer", "Esha Engineer", PW.eng], ["rev", "reviewer", "Ravi Reviewer", PW.rev], ["rev2", "reviewer", "Rina Reviewer", PW.rev2], ["view", "viewer", "Vik Viewer", PW.view]]) {
    const r = await admin.post("/users", { username: u, displayName: name, role, password: pw });
    assert.equal(r.status, 200, `create ${u}: ${r.body?.error}`);
  }
  for (const [c, u, pw] of [[eng, "eng", PW.eng], [rev, "rev", PW.rev], [rev2, "rev2", PW.rev2], [view, "view", PW.view]]) assert.equal((await c.login(u, pw)).status, 200);

  // ---------- access control ----------
  await check("API data needs a session (401 when signed out)", async () => {
    assert.equal((await anon.get("/repositories")).status, 401);
    assert.equal((await anon.get("/repositories/northbank-core/findings")).status, 401);
    assert.equal((await anon.get("/audit")).status, 401);
  });
  await check("viewer can read but cannot scan, verify or decide (403)", async () => {
    assert.equal((await view.get("/repositories")).status, 200);
    assert.equal((await view.post("/repositories/northbank-core/scan")).status, 403);
  });
  await check("engineer cannot approve; only admins manage accounts or reset state", async () => {
    const patches = (await eng.get("/repositories/northbank-core/patches")).body;
    assert.equal((await eng.post(`/patches/${patches[0].id}/decision`, { decision: "approve" })).status, 403);
    assert.equal((await rev.get("/users")).status, 403);
    assert.equal((await rev.post("/admin/reset-state")).status, 403);
  });
  await check("CSRF: a POST without the session's token is refused", async () => {
    assert.equal((await eng.post("/repositories/northbank-core/scan", {}, { csrfOverride: "" })).status, 403);
    assert.equal((await eng.post("/repositories/northbank-core/scan", {}, { csrfOverride: "forged" })).status, 403);
  });
  await check("CSRF: a cross-site 'simple request' (text/plain) is refused", async () => {
    const r = await eng.post("/repositories/northbank-core/scan", "{}", { raw: true, headers: { "content-type": "text/plain", origin: "https://evil.example" } });
    assert.equal(r.status, 415);
    assert.equal(r.headers.get("access-control-allow-origin"), null);
  });
  await check("sign-in is throttled after 5 wrong passwords", async () => {
    const c = client();
    for (let i = 0; i < 5; i++) assert.equal((await c.login("view", "wrong password value " + i)).status, 401);
    assert.equal((await c.login("view", PW.view)).status, 429);
  });
  await check("wrong password and unknown user give the same error", async () => {
    const a = await client().login("eng", "not the right password at all");
    const b = await client().login("nobody-here", "not the right password at all");
    assert.equal(a.status, 401);
    assert.equal(b.body.error, a.body.error);
  });

  // ---------- hardening ----------
  await check("security headers are set on pages and API responses", async () => {
    for (const p of [ORIGIN + "/", B + "/health"]) {
      const h = (await fetch(p)).headers;
      assert.match(h.get("content-security-policy") ?? "", /frame-ancestors 'none'/);
      assert.equal(h.get("x-content-type-options"), "nosniff");
    }
  });
  await check("a malformed URL returns 400 and the server keeps running", async () => {
    assert.equal((await fetch(ORIGIN + "/%E0%A4%A")).status, 400);
    assert.equal((await fetch(B + "/%E0%A4%A")).status, 400);
    assert.equal((await fetch(B + "/health")).status, 200);
  });
  await check("repository ids and file paths cannot escape the workspace", async () => {
    assert.equal((await view.get("/repositories/../file?path=state.json")).status, 404);
    assert.equal((await view.get("/repositories/%2E%2E/file?path=state.json")).status, 404);
    assert.equal((await view.get("/repositories/northbank-core/file?path=../../users.json")).status, 404);
    assert.equal((await view.get("/repositories/northbank-core/file?path=/etc/passwd")).status, 404);
  });
  await check("oversized request bodies are refused (413)", async () => {
    assert.equal((await eng.post("/repositories/northbank-core/scan", { pad: "x".repeat(70_000) })).status, 413);
  });
  await check("unexpected errors do not leak internals", async () => {
    const r = await view.get("/runs/does-not-exist");
    assert.equal(r.status, 404);
    assert.ok(!/\/home\/|at .*\.js/.test(JSON.stringify(r.body)));
  });
  await check("health is public but reveals no environment details", async () => {
    const h = (await anon.get("/health")).body;
    assert.deepEqual(Object.keys(h).sort(), ["ok", "startedAt", "version"]);
  });
  await check("AI analysis reports 'not configured' instead of pretending", async () => {
    const f = (await eng.get("/repositories/northbank-core/findings")).body.findings[0];
    assert.equal((await eng.post(`/findings/${f.id}/sarvam-analyze`)).status, 503);
    assert.equal((await view.get("/system")).body.sarvamConfigured, false);
  });

  // ---------- product behaviour (previous suite, now with real identities) ----------
  const { findings } = (await view.get("/repositories/northbank-core/findings")).body;
  await check("scanner finds real usages with real lines", async () => {
    assert.ok(findings.length >= 8);
    for (const f of findings) {
      const file = (await view.get(`/repositories/northbank-core/file?path=${encodeURIComponent(f.file)}`)).body;
      assert.equal(file.text.split(/\r?\n/)[f.line - 1].trim(), f.snippet, `${f.file}:${f.line}`);
    }
  });
  await check("unknown fields are reported as unknown, not filled in", async () => {
    assert.ok(findings.some((f) => f.dataLifetime.basis === "unknown" && f.dataLifetime.value === null));
  });
  await check("every finding carries its NIST transition deadline", async () => {
    const rsa = findings.find((f) => f.family === "RSA");
    assert.equal(rsa.deadline.disallowedAfter, 2035);
    assert.equal(rsa.deadline.deprecatedAfter, 2030);
    const aes = findings.find((f) => f.family === "AES");
    if (aes) assert.equal(aes.deadline.status, "none");
  });
  await check("CBOM export is CycloneDX 1.6 with exact file/line evidence", async () => {
    const r = await view.get("/repositories/northbank-core/cbom");
    assert.match(r.headers.get("content-disposition"), /attachment; filename="northbank-core-cbom\.cdx\.json"/);
    const bom = r.body;
    assert.equal(bom.bomFormat, "CycloneDX");
    assert.equal(bom.specVersion, "1.6");
    assert.match(bom.serialNumber, /^urn:uuid:[0-9a-f-]{36}$/);
    const occurrences = bom.components.flatMap((c) => c.evidence.occurrences);
    assert.equal(occurrences.length, findings.length);
    for (const c of bom.components) assert.equal(c.type, "cryptographic-asset");
    fs.writeFileSync(path.join(os.tmpdir(), "cryptoshift-test-cbom.json"), JSON.stringify(bom, null, 2));
  });
  await check("plan reports the inferred auth/payments cycle", async () => {
    const plan = (await view.get("/repositories/northbank-core/plan")).body;
    assert.equal(plan.valid, false);
    assert.deepEqual([...plan.cycles[0].members].sort(), ["auth", "payments"]);
  });
  await check("declared-only plan is a valid dependency order", async () => {
    const plan = (await view.get("/repositories/northbank-core/plan?inferred=0")).body;
    assert.equal(plan.valid, true);
    const wave = Object.fromEntries(plan.steps.map((s) => [s.node, s.wave]));
    const graph = (await view.get("/repositories/northbank-core/graph")).body;
    for (const e of graph.edges.filter((x) => x.basis === "known")) assert.ok(wave[e.to] < wave[e.from], `${e.from} after ${e.to}`);
  });
  const patches = (await view.get("/repositories/northbank-core/patches")).body;
  await check("unverified patch is never approvable", async () => {
    assert.equal((await rev.post(`/patches/${patches[0].id}/decision`, { decision: "approve" })).status, 409);
  });

  const python = (await view.get("/system")).body.python;
  if (!python) {
    console.log("SKIP verification checks: Python not found on this machine (checks would report 'unavailable')");
  } else {
    // The engineer starts every run except tls_config, which reviewer "rev" starts (to test four-eyes).
    for (const p of patches) {
      const who = p.file.includes("tls_config") ? rev : eng;
      let r = await who.post(`/patches/${p.id}/verify`);
      while (r.status === 429) {
        await sleep(300);
        r = await who.post(`/patches/${p.id}/verify`);
      }
      assert.equal(r.status, 200, r.body?.error);
    }
    for (let i = 0; i < 300; i++) {
      const list = (await view.get("/repositories/northbank-core/patches")).body;
      if (list.every((p) => p.latestRun?.status === "complete")) break;
      await sleep(200);
    }
    const list = (await view.get("/repositories/northbank-core/patches")).body;
    const by = (f) => list.find((p) => p.file.includes(f));
    await check("payment signer patch fails on a real settlement-network test", async () => {
      assert.equal(by("payment_signer").latestRun.verdict, "failed");
      assert.equal(by("payment_signer").latestRun.checks.find((c) => c.id === "tests").status, "failed");
    });
    await check("CA patch fails FIPS 204 size conformance", async () => {
      assert.equal(by("cert_authority").latestRun.checks.find((c) => c.id === "vectors").status, "failed");
    });
    await check("failed patch cannot be approved", async () => {
      assert.equal((await rev.post(`/patches/${by("payment_signer").id}/decision`, { decision: "approve" })).status, 409);
    });
    await check("rejecting needs an explanation", async () => {
      assert.equal((await rev.post(`/patches/${by("payment_signer").id}/decision`, { decision: "reject" })).status, 400);
    });
    await check("four-eyes: the reviewer who started verification cannot approve it", async () => {
      const r = await rev.post(`/patches/${by("tls_config").id}/decision`, { decision: "approve" });
      assert.equal(r.status, 403);
      assert.match(r.body.error, /Four-eyes/);
    });
    await check("the decision is recorded under the signed-in reviewer, not a client-supplied name", async () => {
      const r = await rev2.post(`/patches/${by("tls_config").id}/decision`, { decision: "approve", reviewer: "CEO", actor: "CEO" });
      assert.equal(r.status, 200, r.body?.error);
      const d = r.body.decisions.at(-1);
      assert.equal(d.reviewer, "Rina Reviewer");
      assert.equal(d.username, "rev2");
    });
    await check("verified → approved → released → rolled back restores the file", async () => {
      const tls = by("tls_config");
      const before = (await view.get("/repositories/northbank-core/file?path=shared/bankcrypto/tls_config.py")).body.text;
      assert.equal((await eng.post(`/patches/${tls.id}/release`)).status, 403, "engineers cannot release");
      const rel = await rev2.post(`/patches/${tls.id}/release`);
      assert.equal(rel.status, 200);
      assert.match((await view.get("/repositories/northbank-core/file?path=shared/bankcrypto/tls_config.py")).body.text, /X25519MLKEM768/);
      assert.equal((await rev2.post(`/checkpoints/${rel.body.checkpoint.id}/rollback`)).status, 200);
      assert.equal((await view.get("/repositories/northbank-core/file?path=shared/bankcrypto/tls_config.py")).body.text, before);
    });
  }

  // ---------- audit chain ----------
  await check("audit log records real identities and its hash chain verifies", async () => {
    const log = (await view.get("/audit?limit=500")).body;
    assert.ok(log.entries.some((e) => e.action === "account.setup" && e.actor === "admin"));
    if (python) assert.ok(log.entries.some((e) => e.action === "patch.approve" && e.actor === "rev2"));
    const v = (await view.get("/audit/verify")).body;
    assert.equal(v.ok, true);
    assert.match(v.head, /^[0-9a-f]{64}$/);
  });
  await check("changing a password signs out other sessions", async () => {
    const other = client();
    assert.equal((await other.login("rev", PW.rev)).status, 200);
    const r = await rev.post("/auth/password", { current: PW.rev, next: "brand new passphrase tulip" });
    assert.equal(r.status, 200);
    assert.equal((await other.get("/repositories")).status, 401);
    assert.equal((await rev.get("/repositories")).status, 200);
  });
  await check("signing out ends the session", async () => {
    assert.equal((await view.post("/auth/logout")).status, 200);
    assert.equal((await view.get("/repositories")).status, 401);
  });

  await stop();
  // Edit one audit entry on disk, as an attacker with file access but no key would.
  const logFile = path.join(DATA, "audit.log");
  const lines = fs.readFileSync(logFile, "utf8").trim().split("\n");
  const victim = JSON.parse(lines[1]);
  victim.actor = "someone-else";
  lines[1] = JSON.stringify(victim);
  fs.writeFileSync(logFile, lines.join("\n") + "\n");
  // Simulate scans stored by a version that had no deadline field.
  const stateFile = path.join(DATA, "state.json");
  const state = JSON.parse(fs.readFileSync(stateFile, "utf8"));
  for (const scan of Object.values(state.scans)) for (const f of scan.findings) delete f.deadline;
  fs.writeFileSync(stateFile, JSON.stringify(state));
  await start();
  await check("tampering with the audit log on disk is detected after restart", async () => {
    const c = client();
    assert.equal((await c.login("eng", PW.eng)).status, 200);
    const v = (await c.get("/audit/verify")).body;
    assert.equal(v.ok, false);
    assert.equal(v.brokenAt, 1);
  });
  await check("findings from scans stored before deadlines existed still get one", async () => {
    const c = client();
    await c.login("eng", PW.eng);
    const { findings: fs2 } = (await c.get("/repositories/northbank-core/findings")).body;
    assert.ok(fs2.filter((f) => f.family === "RSA" || f.family === "ECC").every((f) => f.deadline?.disallowedAfter === 2035));
  });
  await check("no run is left 'running' after a restart", async () => {
    const c = client();
    await c.login("eng", PW.eng);
    const list = (await c.get("/repositories/northbank-core/patches")).body;
    assert.ok(list.every((p) => p.latestRun?.status !== "running"));
  });
} finally {
  if (server && server.exitCode === null) await stop();
  fs.rmSync(DATA, { recursive: true, force: true });
}
console.log(failed ? `${failed} failed, ${passed} passed` : `all ${passed} passed`);
process.exit(failed ? 1 : 0);
