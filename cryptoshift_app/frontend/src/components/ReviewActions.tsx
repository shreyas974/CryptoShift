import * as React from "react";
import { Link } from "react-router-dom";
import { mutate, ApiError } from "../api/client";
import type { Patch } from "../api/types";
import { useApp } from "./Shell";

/** Verification, human decision, release and rollback controls. The backend enforces every gate;
 *  these buttons only expose what it allows and show its refusal verbatim. */
export function ReviewActions({ patch, checkpointId }: { patch: Patch; checkpointId?: string | null }) {
  const { reviewer } = useApp();
  const [note, setNote] = React.useState("");
  const [busy, setBusy] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const run = patch.latestRun;
  const verified = run?.status === "complete" && run.verdict === "verified_candidate";
  const act = async (label: string, path: string, body: unknown) => {
    setBusy(label);
    setError(null);
    try {
      await mutate(path, body);
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(null);
    }
  };
  return (
    <div className="review-actions">
      <div className="kv">
        <button className="btn" disabled={Boolean(busy) || run?.status === "running" || patch.status !== "proposed"} onClick={() => act("verify", `/api/patches/${patch.id}/verify`, { actor: reviewer || undefined })}>
          {run?.status === "running" ? "Verifying…" : run ? "Re-run verification" : "Run verification"}
        </button>
      </div>
      {patch.status === "proposed" ? (
        <div className="gate">
          <strong className="small">Human approval gate</strong>
          {!reviewer ? (
            <p className="small muted">
              Set your reviewer name in <Link to="/settings">Settings</Link> to record a decision.
            </p>
          ) : (
            <p className="small muted">Deciding as <strong>{reviewer}</strong>.</p>
          )}
          <textarea aria-label="Review note" placeholder="Review note (optional)" value={note} onChange={(e) => setNote(e.target.value)} rows={2} />
          <div className="kv">
            <button className="btn btn-primary" disabled={!verified || !reviewer || Boolean(busy)} title={verified ? "" : "Approval opens only when every required check passed"} onClick={() => act("approve", `/api/patches/${patch.id}/decision`, { decision: "approve", reviewer, note })}>
              Approve
            </button>
            <button className="btn" disabled={!reviewer || Boolean(busy)} onClick={() => act("changes", `/api/patches/${patch.id}/decision`, { decision: "request_changes", reviewer, note })}>
              Request changes
            </button>
            <button className="btn btn-danger" disabled={!reviewer || Boolean(busy)} onClick={() => act("reject", `/api/patches/${patch.id}/decision`, { decision: "reject", reviewer, note })}>
              Reject
            </button>
          </div>
          {!verified ? <p className="small muted">Approve stays locked until the latest run is a verified candidate.</p> : null}
        </div>
      ) : null}
      {patch.status === "approved" ? (
        <button className="btn btn-primary" disabled={Boolean(busy)} onClick={() => act("release", `/api/patches/${patch.id}/release`, { actor: reviewer || "unknown" })}>
          Release to working copy (creates rollback checkpoint)
        </button>
      ) : null}
      {patch.status === "released" && checkpointId ? (
        <button className="btn btn-danger" disabled={Boolean(busy)} onClick={() => act("rollback", `/api/checkpoints/${checkpointId}/rollback`, { actor: reviewer || "unknown" })}>
          Roll back to checkpoint
        </button>
      ) : null}
      {error ? (
        <div className="state state-error small" role="alert">
          Backend refused: {error}
        </div>
      ) : null}
    </div>
  );
}
