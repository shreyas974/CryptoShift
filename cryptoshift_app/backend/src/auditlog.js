// Tamper-evident audit log. Each entry is appended to an append-only JSONL file and carries
// mac = HMAC-SHA256(key, canonical(entry fields + previous mac)), so editing, deleting or
// reordering any entry breaks every MAC after it. The key lives beside the log (mode 0600):
// this detects tampering with the log file, not an attacker who also holds the key (see SECURITY.md).
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const GENESIS = "0".repeat(64);

export function openAuditLog(dir) {
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, "audit.log");
  const keyFile = path.join(dir, "audit.key");
  if (!fs.existsSync(keyFile)) fs.writeFileSync(keyFile, crypto.randomBytes(32).toString("hex"), { mode: 0o600 });
  const key = Buffer.from(fs.readFileSync(keyFile, "utf8").trim(), "hex");

  const entries = [];
  if (fs.existsSync(file)) {
    for (const line of fs.readFileSync(file, "utf8").split("\n")) {
      if (!line.trim()) continue;
      try {
        entries.push(JSON.parse(line));
      } catch {
        entries.push({ corrupt: line }); // kept so verify() reports it rather than silently dropping it
      }
    }
  }

  const macOf = (e) => crypto.createHmac("sha256", key).update(JSON.stringify([e.seq, e.at, e.actor, e.action, e.detail, e.legacy ?? false, e.prev])).digest("hex");

  function append(action, detail, actor = "system", extra = {}) {
    const last = entries[entries.length - 1];
    const entry = { seq: entries.length, at: extra.at ?? new Date().toISOString(), actor: String(actor), action: String(action), detail: String(detail ?? ""), ...(extra.legacy ? { legacy: true } : {}), prev: last?.mac ?? GENESIS };
    entry.mac = macOf(entry);
    fs.appendFileSync(file, JSON.stringify(entry) + "\n", { mode: 0o600 });
    entries.push(entry);
    return entry;
  }

  function verify() {
    let prev = GENESIS;
    for (let i = 0; i < entries.length; i++) {
      const e = entries[i];
      if (e.corrupt !== undefined) return { ok: false, entries: entries.length, brokenAt: i, reason: "Unreadable entry" };
      if (e.seq !== i) return { ok: false, entries: entries.length, brokenAt: i, reason: "Entry missing or out of order" };
      if (e.prev !== prev) return { ok: false, entries: entries.length, brokenAt: i, reason: "Chain link does not match the previous entry" };
      const expected = macOf(e);
      if (typeof e.mac !== "string" || e.mac.length !== expected.length || !crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(e.mac))) {
        return { ok: false, entries: entries.length, brokenAt: i, reason: "Entry content was modified" };
      }
      prev = e.mac;
    }
    return { ok: true, entries: entries.length, head: prev, brokenAt: null, reason: null };
  }

  /** Newest first, without MAC internals the UI does not need. */
  function list({ limit = 200, offset = 0 } = {}) {
    const out = [];
    for (let i = entries.length - 1 - offset; i >= 0 && out.length < limit; i--) {
      const e = entries[i];
      if (e.corrupt === undefined) out.push({ id: `${e.seq}`, seq: e.seq, at: e.at, actor: e.actor, action: e.action, detail: e.detail, legacy: e.legacy ?? false });
    }
    return { total: entries.length, entries: out };
  }

  function clear() {
    entries.length = 0;
    fs.rmSync(file, { force: true });
  }

  return { append, verify, list, clear, size: () => entries.length };
}
