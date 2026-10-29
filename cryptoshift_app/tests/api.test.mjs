// Backend integration test: starts the API on a spare port against a fresh state and checks
// the honesty guarantees end to end. Run: npm test
import { spawn } from "node:child_process";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const PORT = 18787;
const B = `http://localhost:${PORT}/api`;
const data = path.resolve("backend/data");
const backup = fs.existsSync(data) ? fs.mkdtempSync(path.join(path.resolve("."), ".test-backup-")) : null;
if (backup) fs.cpSync(data, path.join(backup, "data"), { recursive: true });
fs.rmSync(data, { recursive: true, force: true });

const server = spawn(process.execPath, ["backend/src/server.js"], { env: { ...process.env, PORT: String(PORT) }, stdio: "inherit" });
const get = async (p) => (await fetch(B + p)).json();
const post = async (p, body = {}) => {
  const r = await fetch(B + p, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  return { status: r.status, body: await r.json() };
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failed = 0;
const check = async (name, fn) => {
  try {
    await fn();
    console.log("PASS", name);
  } catch (e) {
    failed++;
    console.log("FAIL", name, "-", e.message);
  }
};

try {
  for (let i = 0; i < 50; i++) {
    try { await fetch(B + "/health"); break; } catch { await sleep(100); }
  }
  const health = await get("/health");
  const { findings } = await get("/repositories/northbank-core/findings");
  await check("scanner finds real usages with real lines", async () => {
    assert.ok(findings.length >= 8);
    for (const f of findings) {
      const file = await get(`/repositories/northbank-core/file?path=${encodeURIComponent(f.file)}`);
      assert.equal(file.text.split(/\r?\n/)[f.line - 1].trim(), f.snippet, `${f.file}:${f.line}`);
    }
  });
  await check("unknown fields are reported as unknown, not filled in", async () => {
    assert.ok(findings.some((f) => f.dataLifetime.basis === "unknown" && f.dataLifetime.value === null));
  });
  await check("plan reports the inferred auth/payments cycle", async () => {
    const plan = await get("/repositories/northbank-core/plan");
    assert.equal(plan.valid, false);
    assert.deepEqual([...plan.cycles[0].members].sort(), ["auth", "payments"]);
  });
  await check("declared-only plan is a valid dependency order", async () => {
    const plan = await get("/repositories/northbank-core/plan?inferred=0");
    assert.equal(plan.valid, true);
    const wave = Object.fromEntries(plan.steps.map((s) => [s.node, s.wave]));
    const graph = await get("/repositories/northbank-core/graph");
    for (const e of graph.edges.filter((x) => x.basis === "known")) assert.ok(wave[e.to] < wave[e.from], `${e.from} after ${e.to}`);
  });
  const patches = await get("/repositories/northbank-core/patches");
  await check("unverified patch is never approvable", async () => {
    const r = await post(`/patches/${patches[0].id}/decision`, { decision: "approve", reviewer: "test" });
    assert.equal(r.status, 409);
  });
  if (!health.python) {
    console.log("SKIP verification checks: Python not found on this machine (checks would report 'unavailable')");
  } else {
    for (const p of patches) await post(`/patches/${p.id}/verify`);
    for (let i = 0; i < 100; i++) {
      const list = await get("/repositories/northbank-core/patches");
      if (list.every((p) => p.latestRun?.status === "complete")) break;
      await sleep(200);
    }
    const list = await get("/repositories/northbank-core/patches");
    const by = (f) => list.find((p) => p.file.includes(f));
    await check("payment signer patch fails on a real settlement-network test", async () => {
      assert.equal(by("payment_signer").latestRun.verdict, "failed");
      assert.equal(by("payment_signer").latestRun.checks.find((c) => c.id === "tests").status, "failed");
    });
    await check("CA patch fails FIPS 204 size conformance", async () => {
      assert.equal(by("cert_authority").latestRun.checks.find((c) => c.id === "vectors").status, "failed");
    });
    await check("failed patch cannot be approved", async () => {
      const r = await post(`/patches/${by("payment_signer").id}/decision`, { decision: "approve", reviewer: "test" });
      assert.equal(r.status, 409);
    });
    await check("approval needs a named reviewer", async () => {
      const r = await post(`/patches/${by("tls_config").id}/decision`, { decision: "approve" });
      assert.equal(r.status, 400);
    });
    await check("verified → approved → released → rolled back restores the file", async () => {
      const tls = by("tls_config");
      assert.equal(tls.latestRun.verdict, "verified_candidate");
      const before = (await get("/repositories/northbank-core/file?path=shared/bankcrypto/tls_config.py")).text;
      assert.equal((await post(`/patches/${tls.id}/decision`, { decision: "approve", reviewer: "test" })).status, 200);
      const rel = await post(`/patches/${tls.id}/release`, { actor: "test" });
      assert.equal(rel.status, 200);
      assert.match((await get("/repositories/northbank-core/file?path=shared/bankcrypto/tls_config.py")).text, /X25519MLKEM768/);
      assert.equal((await post(`/checkpoints/${rel.body.checkpoint.id}/rollback`, { actor: "test" })).status, 200);
      assert.equal((await get("/repositories/northbank-core/file?path=shared/bankcrypto/tls_config.py")).text, before);
    });
  }
} finally {
  server.kill();
  await sleep(300);
  fs.rmSync(data, { recursive: true, force: true });
  if (backup) {
    fs.cpSync(path.join(backup, "data"), data, { recursive: true });
    fs.rmSync(backup, { recursive: true, force: true });
  }
}
console.log(failed ? `${failed} failed` : "all passed");
process.exit(failed ? 1 : 0);
