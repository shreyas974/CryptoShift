// Persistent JSON state (scans, patches, verification runs, checkpoints) plus the
// tamper-evident audit log (auditlog.js), which survives state resets on purpose.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { openAuditLog } from "./auditlog.js";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
export const DATA_DIR = process.env.CRYPTOSHIFT_DATA_DIR
  ? path.resolve(process.env.CRYPTOSHIFT_DATA_DIR)
  : process.env.VERCEL
    ? path.join("/tmp", "cryptoshift-data")
    : path.join(ROOT, "backend", "data");
export const WORKSPACES = path.join(DATA_DIR, "workspaces");
const STATE_FILE = path.join(DATA_DIR, "state.json");

const empty = () => ({ scans: {}, patches: {}, runs: {}, checkpoints: {} });

let state = empty();
let legacyAudit = [];
try {
  if (fs.existsSync(STATE_FILE)) {
    const loaded = JSON.parse(fs.readFileSync(STATE_FILE, "utf8"));
    legacyAudit = Array.isArray(loaded.audit) ? loaded.audit : [];
    delete loaded.audit;
    state = { ...empty(), ...loaded };
  }
} catch (error) {
  console.warn("[store] could not read state, starting fresh:", error.message);
}

export const auditLog = openAuditLog(DATA_DIR);
// One-time migration: entries from the old unchained, newest-first audit array become
// "legacy" entries at the start of the chain (their content cannot be proven, so they are labelled).
if (legacyAudit.length && auditLog.size() === 0) {
  for (const e of [...legacyAudit].reverse()) auditLog.append(e.action, e.detail, e.actor, { at: e.at, legacy: true });
}

let pending = null;
export function save() {
  if (pending) return;
  pending = setTimeout(flush, 50);
}
export function flush() {
  if (pending) clearTimeout(pending);
  pending = null;
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}
if (legacyAudit.length) flush(); // rewrite state.json without the migrated array

export const db = () => state;

export function audit(action, detail, actor = "system") {
  auditLog.append(action, detail, actor);
}

export const sha256 = (text) => crypto.createHash("sha256").update(text).digest("hex");
export const shortId = (text) => sha256(text).slice(0, 12);

export function reset() {
  state = empty();
  save();
}
