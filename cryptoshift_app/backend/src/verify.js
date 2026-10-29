// Verification runner. Every check executes for real against two throwaway copies of the
// repository (baseline and candidate). A check that cannot run is "unavailable" or "not_applicable",
// never "passed". "verified_candidate" requires every required check to pass.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { db, save, audit, sha256, shortId } from "./store.js";
import { repoDir } from "./repos.js";
import { patchedText } from "./patches.js";

let python;
export function pythonCommand() {
  if (python !== undefined) return python;
  python = null;
  for (const cmd of [process.env.CRYPTOSHIFT_PYTHON, "python3", "python", "py"].filter(Boolean)) {
    const probe = spawnSync(cmd, ["--version"], { encoding: "utf8" });
    if (probe.status === 0) {
      python = { cmd, version: (probe.stdout || probe.stderr).trim() };
      break;
    }
  }
  return python;
}

function run(cmd, args, cwd, timeoutMs = 60000) {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, { cwd, env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1", PYTHONPATH: cwd } });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => child.kill(), timeoutMs);
    child.stdout.on("data", (d) => (stdout += d));
    child.stderr.on("data", (d) => (stderr += d));
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code, stdout, stderr });
    });
    child.on("error", (error) => {
      clearTimeout(timer);
      resolve({ code: -1, stdout, stderr: String(error) });
    });
  });
}

const CHECKS = [
  { id: "diff", name: "Patch / diff inspection", required: true },
  { id: "build", name: "Build and syntax", required: true },
  { id: "tests", name: "Unit and regression tests", required: true },
  { id: "vectors", name: "Cryptographic parameter conformance", required: true },
  { id: "protocol", name: "Protocol compatibility", required: true },
];

function parseUnittest(output) {
  const ran = Number(output.match(/Ran (\d+) tests?/)?.[1] ?? 0);
  const failing = [...output.matchAll(/^(FAIL|ERROR): (\S+) \(([^)]+)\)/gm)].map((m) => `${m[3]}.${m[2]}`);
  const reasons = [...output.matchAll(/^AssertionError: (.+)$/gm)].map((m) => m[1]);
  return { ran, failing, reasons, ok: /\nOK/.test(output) || /^OK/m.test(output) };
}

export function startRun(patchId, actor) {
  const patch = db().patches[patchId];
  if (!patch) return { error: 404, message: "Patch not found" };
  const running = Object.values(db().runs).find((r) => r.patchId === patchId && r.status === "running");
  if (running) return { run: running };
  const runRecord = {
    id: shortId(`${patchId}:run:${Date.now()}`),
    patchId,
    patchHash: patch.hash,
    repo: patch.repo,
    startedAt: new Date().toISOString(),
    finishedAt: null,
    status: "running",
    verdict: null,
    python: pythonCommand()?.version ?? null,
    checks: CHECKS.map((c) => ({ ...c, status: "queued", detail: "", output: "", startedAt: null, finishedAt: null })),
    traces: null,
  };
  db().runs[runRecord.id] = runRecord;
  save();
  audit("verification.started", `${patch.file}:${patch.line}`, actor || "system");
  execute(runRecord, patch).catch((error) => {
    runRecord.status = "complete";
    runRecord.verdict = "error";
    runRecord.error = String(error);
    runRecord.finishedAt = new Date().toISOString();
    save();
  });
  return { run: runRecord };
}

async function execute(record, patch) {
  const check = (id) => record.checks.find((c) => c.id === id);
  const set = (id, fields) => {
    Object.assign(check(id), fields, fields.status && fields.status !== "running" ? { finishedAt: new Date().toISOString() } : {});
    save();
  };
  const work = fs.mkdtempSync(path.join(os.tmpdir(), "cryptoshift-verify-"));
  const baseline = path.join(work, "baseline");
  const candidate = path.join(work, "candidate");
  try {
    fs.cpSync(repoDir(patch.repo), baseline, { recursive: true, filter: (src) => !src.includes("__pycache__") });
    fs.cpSync(baseline, candidate, { recursive: true });
    const py = pythonCommand();

    // 1. Diff inspection: the patch applies to the current source, touching exactly one line.
    set("diff", { status: "running", startedAt: new Date().toISOString() });
    const target = path.join(candidate, patch.file);
    const source = fs.readFileSync(target, "utf8");
    let applied = null;
    try {
      applied = patchedText(patch, source);
    } catch (error) {
      set("diff", { status: "failed", detail: error.message });
    }
    if (applied !== null) {
      const changed = source.split(/\r?\n/).filter((line, i) => line !== applied.split(/\r?\n/)[i]).length;
      fs.writeFileSync(target, applied);
      set("diff", {
        status: changed === 1 ? "passed" : "failed",
        detail: changed === 1 ? `Applies cleanly to ${patch.file}; 1 line changed (base ${sha256(source).slice(0, 12)})` : `Unexpected change size: ${changed} lines`,
        output: patch.diff,
      });
    }
    const applies = check("diff").status === "passed";
    const skip = (id) => set(id, { status: "blocked", detail: "Not run: the patch did not apply" });

    // 2. Build and syntax.
    if (!applies) skip("build");
    else if (!py) set("build", { status: "unavailable", detail: "Python interpreter not found on the backend host; check could not run" });
    else {
      set("build", { status: "running", startedAt: new Date().toISOString() });
      const out = await run(py.cmd, ["-m", "compileall", "-q", "."], candidate);
      set("build", { status: out.code === 0 ? "passed" : "failed", detail: out.code === 0 ? `compileall succeeded (${py.version})` : "Compilation errors", output: (out.stdout + out.stderr).slice(-4000) });
    }

    // 3. Unit and regression: same suite on baseline and candidate.
    if (!applies) skip("tests");
    else if (!py) set("tests", { status: "unavailable", detail: "Python interpreter not found on the backend host; tests were not executed" });
    else {
      set("tests", { status: "running", startedAt: new Date().toISOString() });
      const args = ["-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"];
      const [b, c] = await Promise.all([run(py.cmd, args, baseline), run(py.cmd, args, candidate)]);
      const pb = parseUnittest(b.stderr + b.stdout);
      const pc = parseUnittest(c.stderr + c.stdout);
      const regressions = pc.failing.filter((t) => !pb.failing.includes(t));
      const ok = c.code === 0 && pc.ran > 0;
      set("tests", {
        status: ok ? "passed" : "failed",
        detail: ok
          ? `${pc.ran}/${pc.ran} tests passed on candidate (baseline ${pb.ran - pb.failing.length}/${pb.ran})`
          : pc.ran === 0
            ? "No tests ran"
            : `${pc.failing.length} of ${pc.ran} failed on candidate; ${regressions.length} regression${regressions.length === 1 ? "" : "s"} vs baseline`,
        baseline: { ran: pb.ran, failing: pb.failing },
        candidate: { ran: pc.ran, failing: pc.failing, reasons: pc.reasons },
        regressions,
        output: (c.stderr + c.stdout).slice(-6000),
      });
    }

    // 4. Parameter conformance for every PQC algorithm the patch introduces.
    if (!applies) skip("vectors");
    else if (!patch.algorithms.length) set("vectors", { status: "not_applicable", required: false, detail: "Patch introduces no post-quantum parameter set" });
    else if (!py) set("vectors", { status: "unavailable", detail: "Python interpreter not found on the backend host" });
    else {
      set("vectors", { status: "running", startedAt: new Date().toISOString() });
      const out = await run(py.cmd, ["-m", "tools.conformance", ...patch.algorithms], candidate);
      let results = [];
      try {
        results = JSON.parse(out.stdout);
      } catch {
        results = [];
      }
      const failed = results.filter((r) => r.status === "failed");
      const passed = results.length && results.every((r) => r.status === "passed");
      set("vectors", {
        status: out.code !== 0 || !results.length ? "failed" : failed.length ? "failed" : passed ? "passed" : "failed",
        detail: results.length ? results.map((r) => `${r.algorithm}: ${r.detail}`).join(" · ") : "Conformance tool produced no result",
        results,
        note: "Size conformance against FIPS 203/204 tables. Not a known-answer test.",
        output: (out.stdout + out.stderr).slice(-3000),
      });
    }

    // 5. Protocol compatibility: model every peer's handshake before and after.
    if (!applies) skip("protocol");
    else if (!py) set("protocol", { status: "unavailable", detail: "Python interpreter not found on the backend host" });
    else {
      set("protocol", { status: "running", startedAt: new Date().toISOString() });
      const [b, c] = await Promise.all([run(py.cmd, ["-m", "tools.negotiate"], baseline), run(py.cmd, ["-m", "tools.negotiate"], candidate)]);
      let tb = null;
      let tc = null;
      try {
        tb = JSON.parse(b.stdout);
        tc = JSON.parse(c.stdout);
      } catch {
        /* handled below */
      }
      if (!tb || !tc) set("protocol", { status: "failed", detail: "Negotiation model failed to run", output: (c.stderr || b.stderr).slice(-3000) });
      else {
        const compare = tb.results.map((rb) => {
          const rc = tc.results.find((x) => x.peer === rb.peer);
          return { peer: rb.peer, baseline: rb, candidate: rc, regression: rb.ok && !rc.ok, changed: rb.group !== rc.group || rb.ok !== rc.ok };
        });
        const regressions = compare.filter((x) => x.regression);
        const changed = compare.filter((x) => x.changed);
        record.traces = { model: "tools/negotiate.py capability model (no live connections)", baselinePolicy: tb.policy, candidatePolicy: tc.policy, peers: compare };
        set("protocol", {
          status: regressions.length ? "failed" : "passed",
          required: patch.touchesProtocol || regressions.length > 0,
          detail: regressions.length
            ? `${regressions.length} peer${regressions.length === 1 ? "" : "s"} that negotiate today would fail: ${regressions.map((r) => r.peer).join(", ")}`
            : changed.length
              ? `No peer regressions; ${changed.length} peer${changed.length === 1 ? "" : "s"} negotiate differently (${changed.map((x) => `${x.peer}: ${x.candidate.group}`).join(", ")})`
              : patch.touchesProtocol
                ? "No peer regressions and no change in negotiated parameters"
                : "Patch does not change the TLS policy; handshake outcomes identical",
        });
      }
    }

    const required = record.checks.filter((c) => c.required);
    record.verdict = required.some((c) => c.status === "failed" || c.status === "blocked")
      ? "failed"
      : required.every((c) => c.status === "passed")
        ? "verified_candidate"
        : "incomplete";
  } finally {
    fs.rmSync(work, { recursive: true, force: true });
  }
  record.status = "complete";
  record.finishedAt = new Date().toISOString();
  save();
  audit("verification.completed", `${patch.file}:${patch.line} → ${record.verdict}`);
}
