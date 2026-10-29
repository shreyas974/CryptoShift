// Candidate patch proposer, human decisions, controlled release and rollback.
// The proposer is a deterministic rule engine. No LLM is configured in this build;
// proposals are labelled with the engine that produced them.
import fs from "node:fs";
import path from "node:path";
import { db, save, audit, sha256, shortId } from "./store.js";
import { readFile, repoDir } from "./repos.js";

export function getSarvamKey() {
  if (process.env.SARVAM_API_KEY) return process.env.SARVAM_API_KEY;
  try {
    const candidatePaths = [
      path.resolve(process.cwd(), "..", ".env"),
      path.resolve(process.cwd(), ".env"),
      path.resolve(process.cwd(), "..", "..", ".env"),
    ];
    for (const p of candidatePaths) {
      if (fs.existsSync(p)) {
        const text = fs.readFileSync(p, "utf-8");
        const match = text.match(/^\s*SARVAM_API_KEY\s*=\s*(.+)$/m);
        if (match) {
          process.env.SARVAM_API_KEY = match[1].trim();
          return process.env.SARVAM_API_KEY;
        }
      }
    }
  } catch {}
  return null;
}

export async function askSarvam(prompt) {
  const key = getSarvamKey();
  if (!key) throw new Error("Sarvam API key not configured in .env");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);
  try {
    const res = await fetch("https://api.sarvam.ai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "api-subscription-key": key,
      },
      body: JSON.stringify({
        model: "sarvam-105b-conversations",
        messages: [{ role: "user", content: prompt }],
        max_tokens: 400,
        temperature: 0.2,
      }),
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`HTTP ${res.status}: ${errText}`);
    }
    const data = await res.json();
    return data.choices?.[0]?.message?.content?.trim() || "";
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

export const PROPOSER = "rule-engine/1.0 (no LLM configured)";

function transformFor(finding) {
  const line = finding.snippet;
  const vendor = finding.service?.kind === "third-party";
  if (vendor) return { blocked: "Vendored third-party code is not patched in place. Request a PQC-capable release from the vendor." };
  switch (finding.rule) {
    case "keypair-rsa": {
      const target = /Certificate/.test(finding.role.value ?? "") ? "ML-DSA-87" : "ML-DSA-65";
      return { from: /generate_keypair\("RSA",\s*\d+\)/, to: `generate_keypair("${target}")`, algorithms: [target], protocol: false, rationale: `Replace ${finding.algorithm} with ${target} (FIPS 204) for ${finding.role.value?.toLowerCase() ?? "this usage"}.` };
    }
    case "keypair-ec": {
      const target = finding.algorithm === "ECDH-P256" ? "ML-KEM-768" : "ML-DSA-65";
      return { from: new RegExp(`generate_keypair\\("${finding.algorithm}"\\)`), to: `generate_keypair("${target}")`, algorithms: [target], protocol: false, rationale: `Replace ${finding.algorithm} with ${target} (${target.startsWith("ML-KEM") ? "FIPS 203" : "FIPS 204"}).` };
    }
    case "tls-groups":
      return { from: /KEY_EXCHANGE_GROUPS\s*=\s*\[/, to: 'KEY_EXCHANGE_GROUPS = ["X25519MLKEM768", ', algorithms: ["ML-KEM-768"], protocol: true, rationale: "Offer the hybrid X25519MLKEM768 group first while keeping classical groups for peers that do not support it yet." };
    case "hash-sha1":
      return { from: /checksum\("SHA1"/, to: 'checksum("SHA-256"', algorithms: [], protocol: false, rationale: "Replace SHA-1 with SHA-256 (classical hardening, not a post-quantum change)." };
    case "tls-cert":
      return { blocked: "Certificate signature changes follow the PKI migration: the internal CA must issue PQC or hybrid certificates first." };
    case "cipher-aes":
      return { blocked: "No change proposed: AES-256-GCM is retained." };
    default:
      return { blocked: "No rule available for this usage." };
  }
}

function unifiedDiff(file, lines, index, replacement) {
  const start = Math.max(0, index - 3);
  const end = Math.min(lines.length, index + 4);
  const out = [`--- a/${file}`, `+++ b/${file}`, `@@ -${start + 1},${end - start} +${start + 1},${end - start} @@`];
  for (let i = start; i < end; i++) {
    if (i === index) {
      out.push(`-${lines[i]}`);
      out.push(`+${replacement}`);
    } else out.push(` ${lines[i]}`);
  }
  return out.join("\n");
}

export function proposeFor(finding) {
  const existing = Object.values(db().patches).find((p) => p.findingId === finding.id && !["rejected", "rolled_back"].includes(p.status));
  if (existing) return existing;
  const rule = transformFor(finding);
  if (rule.blocked) return { findingId: finding.id, blocked: rule.blocked };
  const text = readFile(finding.repo, finding.file);
  const lines = text.split(/\r?\n/);
  const index = finding.line - 1;
  if (!rule.from.test(lines[index])) return { findingId: finding.id, blocked: "Source line no longer matches the finding; rescan the repository." };
  const after = lines[index].replace(rule.from, rule.to);
  const patch = {
    id: shortId(`${finding.id}:${after}:${Date.now()}`),
    findingId: finding.id,
    repo: finding.repo,
    service: finding.service,
    file: finding.file,
    line: finding.line,
    before: lines[index],
    after,
    diff: unifiedDiff(finding.file, lines, index, after),
    algorithms: rule.algorithms,
    fromAlgorithm: finding.algorithm,
    touchesProtocol: rule.protocol,
    rationale: rule.rationale,
    proposer: PROPOSER,
    baseHash: sha256(text),
    hash: sha256(`${finding.file}:${finding.line}:${after}`),
    status: "proposed",
    createdAt: new Date().toISOString(),
    decisions: [],
    release: null,
  };
  db().patches[patch.id] = patch;
  save();
  audit("patch.proposed", `${patch.file}:${patch.line} ${finding.algorithm} → ${rule.algorithms.join(", ") || rule.to}`, PROPOSER);
  return patch;
}

export function patchedText(patch, sourceText) {
  const lines = sourceText.split(/\r?\n/);
  if (lines[patch.line - 1] !== patch.before) throw new Error(`line ${patch.line} of ${patch.file} no longer matches the patch base`);
  lines[patch.line - 1] = patch.after;
  return lines.join("\n");
}

export function latestRun(patchId) {
  return Object.values(db().runs)
    .filter((r) => r.patchId === patchId)
    .sort((a, b) => b.startedAt.localeCompare(a.startedAt))[0] ?? null;
}

export function decide(patchId, { decision, reviewer, note, actor, reason }) {
  const patch = db().patches[patchId];
  if (!patch) return { error: 404, message: "Patch not found" };
  const effectiveReviewer = (reviewer || actor || "").trim();
  const effectiveNote = note ?? reason ?? "";
  if (!effectiveReviewer) return { error: 400, message: "A named reviewer is required" };
  if (!["approve", "reject", "request_changes"].includes(decision)) return { error: 400, message: "Unknown decision" };
  if (patch.status !== "proposed") return { error: 409, message: `Patch is ${patch.status}; decisions are only taken on proposed patches` };
  if (decision === "approve") {
    const run = latestRun(patchId);
    if (!run || run.status !== "complete") return { error: 409, message: "Approval requires a completed verification run" };
    if (run.verdict !== "verified_candidate") return { error: 409, message: `Approval blocked: latest verification verdict is ${run.verdict}` };
    if (run.patchHash !== patch.hash) return { error: 409, message: "Verification ran against a different patch revision" };
  }
  const record = { decision, reviewer: effectiveReviewer, note: effectiveNote, at: new Date().toISOString(), runId: latestRun(patchId)?.id ?? null };
  patch.decisions.push(record);
  if (decision === "approve") patch.status = "approved";
  if (decision === "reject") patch.status = "rejected";
  save();
  audit(`patch.${decision}`, `${patch.file}:${patch.line}${effectiveNote ? " — " + effectiveNote : ""}`, record.reviewer);
  return { patch };
}

export function release(patchId, actor) {
  const patch = db().patches[patchId];
  if (!patch) return { error: 404, message: "Patch not found" };
  if (patch.status !== "approved") return { error: 409, message: "Only human-approved patches can be released" };
  const full = path.join(repoDir(patch.repo), patch.file);
  const original = fs.readFileSync(full, "utf8");
  let next;
  try {
    next = patchedText(patch, original);
  } catch (error) {
    return { error: 409, message: error.message };
  }
  const checkpoint = {
    id: shortId(`${patch.id}:checkpoint:${Date.now()}`),
    patchId: patch.id,
    repo: patch.repo,
    file: patch.file,
    createdAt: new Date().toISOString(),
    originalHash: sha256(original),
    releasedHash: sha256(next),
    original,
    status: "active",
    restoredAt: null,
  };
  fs.writeFileSync(full, next);
  db().checkpoints[checkpoint.id] = checkpoint;
  patch.status = "released";
  patch.release = { at: checkpoint.createdAt, by: actor || "unknown", checkpointId: checkpoint.id };
  save();
  audit("patch.released", `${patch.file}:${patch.line} written to working copy; checkpoint ${checkpoint.id}`, actor || "unknown");
  return { patch, checkpoint };
}

export function rollback(checkpointId, actor) {
  const checkpoint = db().checkpoints[checkpointId];
  if (!checkpoint) return { error: 404, message: "Checkpoint not found" };
  if (checkpoint.status !== "active") return { error: 409, message: "Checkpoint already restored" };
  const full = path.join(repoDir(checkpoint.repo), checkpoint.file);
  const current = fs.readFileSync(full, "utf8");
  if (sha256(current) !== checkpoint.releasedHash) return { error: 409, message: "File changed after release; refusing to overwrite. Resolve manually." };
  fs.writeFileSync(full, checkpoint.original);
  checkpoint.status = "restored";
  checkpoint.restoredAt = new Date().toISOString();
  const patch = db().patches[checkpoint.patchId];
  if (patch) patch.status = "rolled_back";
  save();
  audit("rollback.restored", `${checkpoint.file} restored to ${checkpoint.originalHash.slice(0, 12)}`, actor || "unknown");
  return { checkpoint };
}
