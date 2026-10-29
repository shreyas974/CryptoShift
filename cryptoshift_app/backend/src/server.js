// CryptoShift API server (Node.js, no dependencies).
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { db, audit, reset as resetState, save, ROOT } from "./store.js";
import { ensureWorkspaces, listRepos, manifestOf, readFile, resetWorkspace } from "./repos.js";
import { scanRepository } from "./scanner.js";
import { buildGraph } from "./graph.js";
import { proposeFor, latestRun, decide, release, rollback, PROPOSER, getSarvamKey, askSarvam } from "./patches.js";
import { startRun, pythonCommand } from "./verify.js";

const PORT = Number(process.env.PORT ?? 8787);
const STARTED = new Date().toISOString();

ensureWorkspaces();
for (const repo of listRepos()) {
  if (!db().scans[repo.id]) scanRepository(repo.id);
  proposeAll(repo.id);
}

function proposeAll(repoId) {
  for (const finding of db().scans[repoId]?.findings ?? []) proposeFor(finding);
}

const findingById = (id) => Object.values(db().scans).flatMap((s) => s.findings).find((f) => f.id === id) ?? null;

function patchView(patch) {
  if (!patch?.id) return patch ?? null;
  const run = latestRun(patch.id);
  return { ...patch, latestRun: run ? runSummary(run) : null };
}

const runSummary = (run) => ({ id: run.id, status: run.status, verdict: run.verdict, startedAt: run.startedAt, finishedAt: run.finishedAt, patchHash: run.patchHash, checks: run.checks.map(({ output, ...rest }) => rest) });

function activePatchFor(findingId) {
  const list = Object.values(db().patches).filter((p) => p.findingId === findingId).sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  return list.find((p) => !["rejected", "rolled_back"].includes(p.status)) ?? list[0] ?? null;
}

function findingView(finding) {
  const patch = activePatchFor(finding.id);
  const proposal = patch ? null : proposeFor(finding);
  const run = patch ? latestRun(patch.id) : null;
  const verification = !patch
    ? { status: "no_patch", label: proposal?.blocked ?? "No candidate patch" }
    : !run
      ? { status: "not_run", label: "Candidate patch not verified yet" }
      : run.status === "running"
        ? { status: "running", label: "Verification running" }
        : { status: run.verdict, label: run.verdict === "verified_candidate" ? "Verified candidate" : run.verdict === "failed" ? "Verification failed" : "Verification incomplete" };
  return { ...finding, excerpt: finding.excerpt, patch: patch ? { id: patch.id, status: patch.status, after: patch.after } : null, proposalBlocked: proposal?.blocked ?? null, verification };
}

function graphFor(repoId) {
  const scan = db().scans[repoId];
  const manifest = manifestOf(repoId);
  if (!scan || !manifest) return null;
  return buildGraph(manifest, scan.imports);
}

function compatibilityConflicts(repoId) {
  const out = [];
  for (const patch of Object.values(db().patches).filter((p) => p.repo === repoId && p.status === "proposed")) {
    const run = latestRun(patch.id);
    if (!run || run.verdict !== "failed") continue;
    for (const check of run.checks.filter((c) => c.status === "failed")) {
      out.push({ node: patch.service?.id ?? null, patchId: patch.id, file: patch.file, line: patch.line, check: check.name, detail: check.candidate?.reasons?.[0] ?? check.detail });
    }
  }
  return out;
}

// ---------- routing ----------
const routes = [];
const route = (method, pattern, handler) => routes.push({ method, re: new RegExp("^" + pattern.replace(/:(\w+)/g, "(?<$1>[^/]+)") + "$"), handler });

route("GET", "/api/health", () => ({
  ok: true,
  startedAt: STARTED,
  python: pythonCommand()?.version ?? null,
  proposer: getSarvamKey() ? "sarvam-105b-conversations (Sarvam AI Cloud LLM Connected)" : PROPOSER,
  sarvamAvailable: Boolean(getSarvamKey()),
  node: process.version,
}));

route("POST", "/api/patches/:id/sarvam-analyze", async ({ id }) => {
  const patch = db().patches[id];
  if (!patch) throw httpError(404, "Patch not found");
  const prompt = `Act as an expert post-quantum cryptographic security auditor for retail banking systems.
Evaluate this candidate cryptographic migration patch:
File: ${patch.file}:${patch.line}
Current Algorithm: ${patch.fromAlgorithm}
Migrated Target: ${patch.algorithms.join(", ") || "SHA-256"}
Protocol Scope: ${patch.touchesProtocol ? "Interbank peer handshake involved" : "Internal component"}
Diff:
${patch.diff}

Provide a structured 2-to-3 sentence assessment:
1. NIST PQC standard alignment (e.g. FIPS 203 ML-KEM or FIPS 204 ML-DSA).
2. Protection against Shor's algorithm and Harvest-Now-Decrypt-Later (HNDL).
3. Risk or peer compatibility considerations.`;

  try {
    const analysis = await askSarvam(prompt);
    return { ok: true, model: "sarvam-105b-conversations", analysis };
  } catch (e) {
    throw httpError(502, `Sarvam AI: ${e.message}`);
  }
});

route("POST", "/api/findings/:id/sarvam-analyze", async ({ id }) => {
  const finding = findingById(id);
  if (!finding) throw httpError(404, "Finding not found");
  const prompt = `Act as a post-quantum cryptographic architect for banking applications.
Analyze this cryptographic finding:
Algorithm: ${finding.algorithm}
Location: ${finding.file}:${finding.line}
Role: ${finding.role?.value ?? "Unknown"}
Risk Band: ${finding.risk?.band} (Score: ${finding.risk?.score})
Snippet:
${finding.snippet}

Recommend the target NIST PQC algorithm replacement and explain the Harvest-Now-Decrypt-Later (HNDL) mitigation strategy in 2 sentences.`;

  try {
    const analysis = await askSarvam(prompt);
    return { ok: true, model: "sarvam-105b-conversations", analysis };
  } catch (e) {
    throw httpError(502, `Sarvam AI: ${e.message}`);
  }
});

route("GET", "/api/repositories", () =>
  listRepos().map((repo) => {
    const scan = db().scans[repo.id];
    return { ...repo, lastScan: scan ? { id: scan.id, at: scan.at, filesScanned: scan.filesScanned, findings: scan.findings.length } : null };
  }),
);

route("POST", "/api/repositories/:id/scan", ({ id }) => {
  if (!manifestOf(id)) throw httpError(404, "Repository not found");
  const scan = scanRepository(id);
  proposeAll(id);
  return { id: scan.id, at: scan.at, findings: scan.findings.length, filesScanned: scan.filesScanned };
});

route("POST", "/api/repositories/:id/reset", ({ id }) => {
  if (!manifestOf(id)) throw httpError(404, "Repository not found");
  resetWorkspace(id);
  const state = db();
  for (const [key, p] of Object.entries(state.patches)) if (p.repo === id) delete state.patches[key];
  for (const [key, r] of Object.entries(state.runs)) if (r.repo === id) delete state.runs[key];
  for (const [key, c] of Object.entries(state.checkpoints)) if (c.repo === id) delete state.checkpoints[key];
  save();
  audit("repository.reset", `${id} working copy restored from sample source`);
  scanRepository(id);
  proposeAll(id);
  return { ok: true };
});

route("GET", "/api/repositories/:id/findings", ({ id }) => {
  const scan = db().scans[id];
  if (!scan) throw httpError(404, "No scan for this repository");
  return { scan: { id: scan.id, at: scan.at, filesScanned: scan.filesScanned, rules: scan.rules }, findings: scan.findings.map(findingView) };
});

route("GET", "/api/findings/:id", ({ id }) => {
  const finding = findingById(id);
  if (!finding) throw httpError(404, "Finding not found");
  return findingView(finding);
});

route("GET", "/api/repositories/:id/file", ({ id }, query) => {
  const rel = query.get("path") ?? "";
  try {
    return { path: rel, text: readFile(id, rel) };
  } catch {
    throw httpError(404, "File not found in repository");
  }
});

route("GET", "/api/repositories/:id/graph", ({ id }) => {
  const graph = graphFor(id);
  if (!graph) throw httpError(404, "No scan for this repository");
  const findings = db().scans[id].findings;
  return {
    nodes: graph.nodes.map((n) => {
      const own = findings.filter((f) => f.service?.id === n.id);
      return { ...n, findings: own.length, maxRisk: own.reduce((m, f) => Math.max(m, f.risk.score), 0), findingIds: own.map((f) => f.id), dependencies: graph.dependenciesOf(n.id), dependents: graph.dependentsOf(n.id) };
    }),
    edges: graph.edges,
    note: "Known edges are declared in cryptoshift.services.json; inferred edges come from Python imports. Runtime calls not visible in source are not captured.",
  };
});

route("GET", "/api/repositories/:id/plan", ({ id }, query) => {
  const graph = graphFor(id);
  if (!graph) throw httpError(404, "No scan for this repository");
  const includeInferred = query.get("inferred") !== "0";
  return { includeInferred, ...graph.plan({ includeInferred }), compatibility: compatibilityConflicts(id) };
});

route("GET", "/api/repositories/:id/patches", ({ id }) =>
  Object.values(db().patches)
    .filter((p) => p.repo === id)
    .sort((a, b) => a.createdAt.localeCompare(b.createdAt))
    .map(patchView),
);

route("POST", "/api/findings/:id/propose", ({ id }) => {
  const finding = findingById(id);
  if (!finding) throw httpError(404, "Finding not found");
  const result = proposeFor(finding);
  if (result.blocked) throw httpError(409, result.blocked);
  return patchView(result);
});

route("GET", "/api/patches/:id", ({ id }) => {
  const patch = db().patches[id];
  if (!patch) throw httpError(404, "Patch not found");
  const runs = Object.values(db().runs).filter((r) => r.patchId === id).sort((a, b) => b.startedAt.localeCompare(a.startedAt));
  return { ...patchView(patch), finding: findingById(patch.findingId), runs: runs.map(runSummary) };
});

route("POST", "/api/patches/:id/verify", ({ id }, _q, body) => {
  const result = startRun(id, body?.actor);
  if (result.error) throw httpError(result.error, result.message);
  return runSummary(result.run);
});

route("GET", "/api/runs/:id", ({ id }) => {
  const run = db().runs[id];
  if (!run) throw httpError(404, "Run not found");
  return run;
});

route("POST", "/api/patches/:id/decision", ({ id }, _q, body) => {
  const result = decide(id, body ?? {});
  if (result.error) throw httpError(result.error, result.message);
  return patchView(result.patch);
});

route("POST", "/api/patches/:id/release", ({ id }, _q, body) => {
  const result = release(id, body?.actor);
  if (result.error) throw httpError(result.error, result.message);
  return { patch: patchView(result.patch), checkpoint: stripCheckpoint(result.checkpoint) };
});

const stripCheckpoint = ({ original, ...rest }) => rest;

route("GET", "/api/repositories/:id/checkpoints", ({ id }) =>
  Object.values(db().checkpoints)
    .filter((c) => c.repo === id)
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
    .map(stripCheckpoint),
);

route("POST", "/api/checkpoints/:id/rollback", ({ id }, _q, body) => {
  const result = rollback(id, body?.actor);
  if (result.error) throw httpError(result.error, result.message);
  return stripCheckpoint(result.checkpoint);
});

route("GET", "/api/repositories/:id/traces", ({ id }) =>
  Object.values(db().runs)
    .filter((r) => r.repo === id && r.traces)
    .sort((a, b) => b.startedAt.localeCompare(a.startedAt))
    .map((r) => {
      const patch = db().patches[r.patchId];
      return { runId: r.id, patchId: r.patchId, file: patch?.file, line: patch?.line, at: r.startedAt, verdict: r.verdict, traces: r.traces };
    }),
);

route("GET", "/api/audit", () => db().audit);

route("POST", "/api/admin/reset-state", () => {
  resetState();
  for (const repo of listRepos()) {
    resetWorkspace(repo.id);
    scanRepository(repo.id);
    proposeAll(repo.id);
  }
  return { ok: true };
});

// ---------- server ----------
function httpError(status, message) {
  const error = new Error(message);
  error.status = status;
  return error;
}

const STATIC = path.join(ROOT, "frontend", "dist");
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".json": "application/json", ".png": "image/png", ".ico": "image/x-icon" };

export async function handleRequest(req, res) {
  const url = new URL(req.url, "http://localhost");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "content-type");
  if (req.method === "OPTIONS") return res.writeHead(204).end();
  if (!url.pathname.startsWith("/api/")) return serveStatic(url.pathname, res);
  const match = routes.map((r) => ({ r, m: r.method === req.method && url.pathname.match(r.re) })).find((x) => x.m);
  if (!match) return send(res, 404, { error: "Not found" });
  let body = req.body;
  if (req.method === "POST" && (body === undefined || body === null)) {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    try {
      body = chunks.length ? JSON.parse(Buffer.concat(chunks).toString("utf8")) : {};
    } catch {
      return send(res, 400, { error: "Invalid JSON body" });
    }
  }
  try {
    const result = await match.r.handler(match.m.groups ?? {}, url.searchParams, body);
    send(res, 200, result);
  } catch (error) {
    if (!error.status) console.error(error);
    send(res, error.status ?? 500, { error: error.message });
  }
}

const server = http.createServer(handleRequest);

function send(res, status, payload) {
  res.writeHead(status, { "content-type": "application/json" });
  res.end(JSON.stringify(payload));
}

function serveStatic(pathname, res) {
  if (!fs.existsSync(STATIC)) return res.writeHead(404, { "content-type": "text/plain" }).end("Frontend not built. Run `npm run build` or use the Vite dev server.");
  let file = path.join(STATIC, decodeURIComponent(pathname));
  if (!file.startsWith(STATIC) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(STATIC, "index.html");
  res.writeHead(200, { "content-type": TYPES[path.extname(file)] ?? "application/octet-stream" });
  fs.createReadStream(file).pipe(res);
}

if (!process.env.VERCEL) {
  server.listen(PORT, () => console.log(`CryptoShift API on http://localhost:${PORT}  (python: ${pythonCommand()?.version ?? "not found"})`));
}
