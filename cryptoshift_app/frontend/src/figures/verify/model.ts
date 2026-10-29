// Maps a patch and its latest verification run onto the inspection line's stations.
// A station that did not run is never shown as passed.
import type { Check, Checkpoint, Patch, Run } from "../../api/types";
import type { PartStatus } from "../../anatomy/AnatomyFrame";

export type StationId = "legacy" | "candidate" | "diff" | "build" | "tests" | "vectors" | "protocol" | "report" | "approval" | "release" | "rollback";

export interface Station {
  id: StationId;
  label: string;
  status: PartStatus;
  statusLabel: string;
  summary: string;
  readout: string;
  /** Whether the carriage may move past this station. */
  clears: boolean;
  check?: Check;
}

const CHECK_STATUS: Record<Check["status"], [PartStatus, string]> = {
  passed: ["passed", "Passed"],
  failed: ["failed", "Failed"],
  blocked: ["blocked", "Blocked"],
  running: ["pending", "Running"],
  queued: ["pending", "Queued"],
  unavailable: ["pending", "Unavailable"],
  not_applicable: ["neutral", "Not applicable"],
  not_run: ["unrun", "Not run"],
};

export function stationsOf(patch: Patch, run: Run | null, checkpoint: Checkpoint | null): Station[] {
  const check = (id: Check["id"]) => run?.checks.find((c) => c.id === id);
  const fromCheck = (id: Check["id"], label: string, what: string): Station => {
    const c = check(id);
    if (!c) return { id, label, status: "unrun", statusLabel: "Not run", summary: `${what} No verification run yet.`, readout: `${id}: not run`, clears: false };
    const [status, text] = CHECK_STATUS[c.status];
    const optional = !c.required && c.status !== "failed";
    return {
      id,
      label,
      status,
      statusLabel: `${text}${c.required ? "" : " (not required)"}`,
      summary: `${what} ${c.detail || text}.`,
      readout: `${id}: ${text.toLowerCase()}`,
      clears: c.status === "passed" || c.status === "not_applicable" || (optional && c.status !== "running" && c.status !== "queued"),
      check: c,
    };
  };
  const complete = run?.status === "complete";
  const verdict = run?.verdict;
  const approved = patch.status === "approved" || patch.status === "released" || patch.status === "rolled_back";
  const decision = patch.decisions.at(-1);
  return [
    { id: "legacy", label: "Legacy implementation", status: "neutral", statusLabel: "Baseline", summary: `${patch.fromAlgorithm} at ${patch.file}:${patch.line}, the baseline every check compares against.`, readout: patch.fromAlgorithm, clears: true },
    { id: "candidate", label: "Candidate patch", status: patch.status === "rejected" ? "failed" : "pending", statusLabel: patch.status, summary: `${patch.proposer}: ${patch.rationale}`, readout: patch.algorithms.join(", ") || "classical fix", clears: true },
    fromCheck("diff", "Patch / diff inspection", "Applies the diff to a clean copy and confirms its size."),
    fromCheck("build", "Build and syntax checks", "Compiles every module of the candidate copy."),
    fromCheck("tests", "Unit and regression tests", "Runs the same suite on baseline and candidate."),
    fromCheck("vectors", "Cryptographic parameter conformance", "Compares declared PQC sizes with FIPS 203/204 tables (not a known-answer test)."),
    fromCheck("protocol", "Protocol compatibility", "Models each peer's handshake before and after the patch."),
    {
      id: "report",
      label: "Verification report",
      status: !run ? "unrun" : !complete ? "pending" : verdict === "verified_candidate" ? "passed" : verdict === "failed" || verdict === "error" ? "failed" : "pending",
      statusLabel: !run ? "No report" : !complete ? "Running" : verdict === "verified_candidate" ? "Verified candidate" : verdict === "failed" ? "Failed" : "Incomplete",
      summary: !run
        ? "Printed once a run completes."
        : verdict === "verified_candidate"
          ? "Every configured required check passed. This is evidence for review, not proof of absolute security."
          : verdict === "failed"
            ? "A required check failed: the patch returns for revision; nothing reaches the approval gate."
            : "The run is not complete, so no verdict is printed.",
      readout: !run ? "report: none" : `report: ${verdict ?? "running"}`,
      clears: verdict === "verified_candidate",
    },
    {
      id: "approval",
      label: "Human approval control",
      status: approved ? "passed" : patch.status === "rejected" ? "failed" : verdict === "verified_candidate" ? "pending" : "blocked",
      statusLabel: approved ? "Approved" : patch.status === "rejected" ? "Rejected" : verdict === "verified_candidate" ? "Awaiting reviewer" : "Locked",
      summary: approved
        ? `Approved by ${patch.decisions.find((d) => d.decision === "approve")?.reviewer ?? "reviewer"}.`
        : patch.status === "rejected"
          ? `Rejected by ${decision?.reviewer}.`
          : verdict === "verified_candidate"
            ? "Key switch is unlocked. A named human must approve or reject."
            : "Locked: approval opens only for a verified candidate.",
      readout: approved ? "approved" : verdict === "verified_candidate" ? "awaiting human" : "gate locked",
      clears: approved,
    },
    {
      id: "release",
      label: "Release checkpoint",
      status: patch.status === "released" ? "passed" : patch.status === "rolled_back" ? "failed" : approved ? "pending" : "unrun",
      statusLabel: patch.status === "released" ? "Released" : patch.status === "rolled_back" ? "Rolled back" : approved ? "Ready to release" : "Closed",
      summary: patch.status === "released" ? `Written to the working copy by ${patch.release?.by}.` : patch.status === "rolled_back" ? "Released, then rolled back." : approved ? "Barrier can be raised: release writes the patched file and records a checkpoint." : "Barrier closed until a human approves.",
      readout: patch.status === "released" ? "released" : "barrier closed",
      clears: patch.status === "released",
    },
    {
      id: "rollback",
      label: "Rollback checkpoint",
      status: checkpoint ? "passed" : "unrun",
      statusLabel: checkpoint ? (checkpoint.status === "active" ? "Armed" : "Restored") : "No checkpoint",
      summary: checkpoint
        ? checkpoint.status === "active"
          ? `Original file stored (sha256 ${checkpoint.originalHash.slice(0, 12)}…). Rollback restores it byte for byte.`
          : `Restored to ${checkpoint.originalHash.slice(0, 12)}… at ${new Date(checkpoint.restoredAt!).toLocaleString()}.`
        : "Created automatically when a patch is released.",
      readout: checkpoint ? `checkpoint ${checkpoint.status}` : "no checkpoint",
      clears: true,
    },
  ];
}

/** Index of the station the carriage rests at: the first gate on the line it cannot clear. */
export function stopOf(stations: Station[]) {
  const line: StationId[] = ["diff", "build", "tests", "vectors", "protocol", "report", "approval", "release"];
  for (let i = 0; i < line.length; i++) {
    const s = stations.find((x) => x.id === line[i])!;
    if (!s.clears) return i;
  }
  return line.length;
}
