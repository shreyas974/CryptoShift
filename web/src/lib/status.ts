/** Status vocabulary shared with the backend. Anything else is UNKNOWN and is never shown as passed. */
export const KNOWN = [
  "VERIFIED",
  "PARTIAL",
  "MOCKED",
  "SIMULATED",
  "SIMULATOR",
  "SYNTHETIC",
  "PLANNED",
  "BLOCKED",
  "PASS",
  "FAIL",
  "READY",
  "PROPOSED",
  "APPROVED",
  "RUN",
  "OBSERVED",
  "DECLARED",
  "INFERRED",
  "HOLD",
  "NOT RUN",
  "NOT APPLICABLE",
] as const;
export type Status = (typeof KNOWN)[number] | "UNKNOWN";

export function normStatus(value: unknown): Status {
  const s = String(value ?? "")
    .trim()
    .toUpperCase();
  return (KNOWN as readonly string[]).includes(s) ? (s as Status) : "UNKNOWN";
}

type Tone = "ok" | "warn" | "bad" | "sim" | "info" | "neutral";
const MAP: Record<Status, [string, Tone, string]> = {
  VERIFIED: ["✔", "ok", "built and observed with command evidence"],
  PASS: ["✔", "ok", "check passed"],
  READY: ["✔", "ok", "all required gates passed"],
  APPROVED: ["✔", "ok", "approved by a human"],
  RUN: ["✔", "ok", "ran and produced a result"],
  OBSERVED: ["👁", "ok", "evidence in a file with a line number"],
  PARTIAL: ["◐", "warn", "partly done"],
  PROPOSED: ["◐", "warn", "not ready: a gate blocks it"],
  HOLD: ["◐", "warn", "unknown purpose: human review"],
  INFERRED: ["↯", "warn", "assumption with a stated reason"],
  MOCKED: ["⚠", "neutral", "fake data stands in"],
  SYNTHETIC: ["🧪", "neutral", "invented demo data"],
  DECLARED: ["📄", "neutral", "declared in a descriptor only"],
  UNKNOWN: ["?", "neutral", "unrecognised value; never treated as passed"],
  SIMULATED: ["⚛", "sim", "simulator run, not hardware"],
  SIMULATOR: ["⚛", "sim", "simulator run, not hardware"],
  PLANNED: ["⏳", "info", "not built yet"],
  BLOCKED: ["⛔", "bad", "cannot run; reason shown"],
  FAIL: ["✖", "bad", "check failed"],
  "NOT RUN": ["⊘", "neutral", "not executed yet; never counted as a pass"],
  "NOT APPLICABLE": ["–", "neutral", "not required for this step's cryptographic purposes"],
};

export function badgeInfo(value: unknown): { status: Status; icon: string; tone: Tone; meaning: string } {
  const status = normStatus(value);
  const [icon, tone, meaning] = MAP[status];
  return { status, icon, tone, meaning };
}

/** True only for statuses that mean "passed". UNKNOWN is never a pass. */
export const isPass = (value: unknown) => ["PASS", "READY", "APPROVED", "VERIFIED", "RUN"].includes(normStatus(value));

/** Plain text for scanned content: control characters removed and capped. React escapes it on render. */
export function plainText(value: unknown, limit = 160): string {
  // eslint-disable-next-line no-control-regex
  const s = String(value ?? "").replace(/[\u0000-\u0008\u000b-\u001f\u007f]/g, " ");
  return s.length <= limit ? s : `${s.slice(0, limit - 1)}…`;
}

/** Approve is possible only when the backend says READY + every required gate passes, and name + hash prefix match. */
export function canApprove(
  step: { state: string; all_required_gates_pass: boolean } | undefined,
  approver: string,
  typedHash: string,
  planHash: string | null,
  acknowledged: boolean,
): { ok: boolean; reason: string } {
  if (!step) return { ok: false, reason: "choose a step" };
  if (normStatus(step.state) !== "READY") return { ok: false, reason: `step is ${normStatus(step.state)}, not READY` };
  if (!step.all_required_gates_pass) return { ok: false, reason: "not every required gate passes" };
  if (!approver.trim()) return { ok: false, reason: "type your name as approver" };
  const h = typedHash.trim().toLowerCase();
  if (!planHash || h.length < 12 || !planHash.startsWith(h))
    return { ok: false, reason: "type the first 12+ characters of the plan hash" };
  if (!acknowledged) return { ok: false, reason: "confirm that this records your approval" };
  return { ok: true, reason: "ready to approve" };
}
