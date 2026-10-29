// Persistent JSON state: scans, patches, verification runs, decisions, checkpoints, audit log.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

import { fileURLToPath } from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
export const DATA_DIR = process.env.VERCEL ? path.join("/tmp", "cryptoshift-data") : path.join(ROOT, "backend", "data");
export const WORKSPACES = path.join(DATA_DIR, "workspaces");
const STATE_FILE = path.join(DATA_DIR, "state.json");
const SEED_FILE = path.join(ROOT, "backend", "data", "state.json");

const empty = () => ({ scans: {}, patches: {}, runs: {}, checkpoints: {}, audit: [] });

let state = empty();
try {
  if (fs.existsSync(STATE_FILE)) {
    state = { ...empty(), ...JSON.parse(fs.readFileSync(STATE_FILE, "utf8")) };
  } else if (fs.existsSync(SEED_FILE)) {
    state = { ...empty(), ...JSON.parse(fs.readFileSync(SEED_FILE, "utf8")) };
  }
} catch (error) {
  console.warn("[store] could not read state, starting fresh:", error.message);
}

let pending = null;
export function save() {
  if (pending) return;
  pending = setTimeout(() => {
    pending = null;
    fs.mkdirSync(DATA_DIR, { recursive: true });
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
  }, 50);
}

export const db = () => state;

export function audit(action, detail, actor = "system") {
  state.audit.unshift({ id: crypto.randomUUID(), at: new Date().toISOString(), actor, action, detail });
  state.audit = state.audit.slice(0, 500);
  save();
}

export const sha256 = (text) => crypto.createHash("sha256").update(text).digest("hex");
export const shortId = (text) => sha256(text).slice(0, 12);

export function reset() {
  state = empty();
  save();
}
