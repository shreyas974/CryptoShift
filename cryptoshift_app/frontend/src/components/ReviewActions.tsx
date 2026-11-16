import * as React from "react";
import { mutate, ApiError } from "../api/client";
import type { Patch } from "../api/types";
import { useAuth, ROLE_LABEL } from "../auth/Auth";

/** Verification, human decision, release and rollback controls. The backend enforces every gate
 *  (role, verification verdict, four-eyes); these controls explain what is allowed and show any refusal verbatim. */
export function ReviewActions({ patch, checkpointId }: { patch: Patch; checkpointId?: string | null }) {
  const { user, can } = useAuth();
  const [note, setNote] = React.useState("");
  const [busy, setBusy] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [done, setDone] = React.useState<string | null>(null);
  const run = patch.latestRun;
  const verified = run?.status === "complete" && run.verdict === "verified_candidate";
  const startedRun = Boolean(run?.startedBy && run.startedBy === user?.username);
  const act = async (label: string, path: string, body: unknown = {}, success?: string) => {
    setBusy(label);
    setError(null);
    setDone(null);
    try {
      await mutate(path, body);
      if (success) setDone(success);
      if (label !== "verify") setNote("");
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(null);
    }
  };
  const decide = (decision: "approve" | "reject" | "request_changes") => {
    if (decision !== "approve" && !note.trim()) return setError("Add a note explaining what needs to change.");
    void act(decision, `/api/patches/${patch.id}/decision`, { decision, note }, decision === "approve" ? "Approved. A reviewer can now release it." : "Decision recorded.");
  };
  return (
    <div className="review-actions">
      {can("engineer") ? (
        <div className="kv">
          <button className="btn" disabled={Boolean(busy) || run?.status === "running" || patch.status !== "proposed"} onClick={() => act("verify", `/api/patches/${patch.id}/verify`)}>
            {run?.status === "running" ? "Verifying…" : run ? "Re-run verification" : "Run verification"}
          </button>
          {run?.startedBy ? <span className="small muted">Last run started by @{run.startedBy}</span> : null}
        </div>
      ) : null}
      {patch.status === "proposed" ? (
        <div className="gate">
          <strong className="small">Human approval gate</strong>
          {!can("reviewer") ? (
            <p className="small muted">Only reviewers can decide. You are signed in as {user ? ROLE_LABEL[user.role].toLowerCase() : "a guest"}.</p>
          ) : (
            <>
              <p className="small muted">
                Deciding as <strong>{user?.displayName}</strong> (@{user?.username}). Your name is taken from your account, not typed in.
              </p>
              {verified && startedRun ? (
                <p className="small gate-warning" role="note">
                  Four-eyes rule: you started this verification run, so another reviewer has to approve it. You can still request changes or reject.
                </p>
              ) : null}
              <label className="sr-only" htmlFor={`note-${patch.id}`}>
                Review note
              </label>
              <textarea id={`note-${patch.id}`} placeholder="Review note (required to reject or request changes)" value={note} onChange={(e) => setNote(e.target.value)} rows={2} maxLength={1000} />
              <div className="kv">
                <button className="btn btn-primary" disabled={!verified || startedRun || Boolean(busy)} title={!verified ? "Approval opens only when every required check passed" : startedRun ? "Four-eyes: another reviewer must approve" : ""} onClick={() => decide("approve")}>
                  {busy === "approve" ? "Approving…" : "Approve"}
                </button>
                <button className="btn" disabled={Boolean(busy)} onClick={() => decide("request_changes")}>
                  Request changes
                </button>
                <button className="btn btn-danger" disabled={Boolean(busy)} onClick={() => decide("reject")}>
                  Reject
                </button>
              </div>
              {!verified ? <p className="small muted">Approve stays locked until the latest run is a verified candidate.</p> : null}
            </>
          )}
        </div>
      ) : null}
      {patch.status === "approved" && can("reviewer") ? (
        <button className="btn btn-primary" disabled={Boolean(busy)} onClick={() => act("release", `/api/patches/${patch.id}/release`, {}, "Released. A rollback checkpoint was created.")}>
          Release to working copy (creates rollback checkpoint)
        </button>
      ) : null}
      {patch.status === "released" && checkpointId && can("reviewer") ? (
        <button className="btn btn-danger" disabled={Boolean(busy)} onClick={() => act("rollback", `/api/checkpoints/${checkpointId}/rollback`, {}, "Rolled back: the original file is restored.")}>
          Roll back to checkpoint
        </button>
      ) : null}
      {done ? (
        <div className="state small" role="status">
          {done}
        </div>
      ) : null}
      {error ? (
        <div className="state state-error small" role="alert">
          {error}
        </div>
      ) : null}
    </div>
  );
}
