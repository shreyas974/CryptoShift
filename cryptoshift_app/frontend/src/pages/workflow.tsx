import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, useApi, mutate, ApiError, downloadJson } from "../api/client";
import type { AuditList, AuditVerification, Checkpoint, FindingsResponse, Patch, PatchDetail, Plan, Role, Run, SystemInfo, TraceRecord, User } from "../api/types";
import { useAuth, ROLE_LABEL, ROLE_CAN } from "../auth/Auth";
import { useApp } from "../components/Shell";
import { Async, Badge, Card, CheckBadge, Diff, Empty, Field, PageHeader, PatchBadge, VerdictBadge, fmtTime, mono } from "../components/ui";
import { ReviewActions } from "../components/ReviewActions";
import { TraceCompare } from "../components/TraceCompare";
import { VerifyFigure } from "../figures/verify/VerifyFigure";
import { DonutChart, BarChart } from "../components/VisualCharts";

const NoRepo = () => <Empty>No repository is available. Choose one in the top bar, or start the backend if it is offline.</Empty>;

function PatchPicker({ patches, value, onChange }: { patches: Patch[]; value: string; onChange: (id: string) => void }) {
  return (
    <ul className="ax-parts" style={{ maxHeight: "none" }} aria-label="Candidate patches">
      {patches.map((p) => (
        <li key={p.id}>
          <button className="ax-part-btn" aria-pressed={p.id === value} onClick={() => onChange(p.id)} style={{ alignItems: "flex-start" }}>
            <span style={{ flex: 1, display: "grid", gap: 2 }}>
              <span className="mono" style={{ fontSize: 12 }}>{p.file}:{p.line}</span>
              <span className="small muted">{p.fromAlgorithm} → {p.algorithms.join(", ") || "SHA-256"}</span>
            </span>
            <span style={{ display: "grid", gap: 4, justifyItems: "end" }}>
              <PatchBadge status={p.status} />
              <VerdictBadge verdict={p.latestRun ? (p.latestRun.status === "running" ? "running" : p.latestRun.verdict) : "not_run"} />
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function usePatchSelection(poll = false) {
  const { repoId } = useApp();
  const [params, setParams] = useSearchParams();
  const list = useApi<Patch[]>(repoId ? `/api/repositories/${repoId}/patches` : null, poll ? 2500 : undefined);
  const chosen = list.data?.find((p) => p.id === params.get("patch")) ?? list.data?.find((p) => p.status === "proposed") ?? list.data?.[0] ?? null;
  // Pin the initial choice in the URL so a status change never silently switches patches.
  React.useEffect(() => {
    if (chosen && !params.get("patch")) setParams({ patch: chosen.id }, { replace: true });
  }, [chosen, params, setParams]);
  return { repoId, list, chosen, select: (id: string) => setParams({ patch: id }) };
}

function ProposerBanner() {
  const system = useApi<SystemInfo>("/api/system");
  if (!system.data) return null;
  return (
    <div className="banner banner-info" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
      <div>
        <strong>How patches are proposed:</strong> a deterministic rule engine maps each finding to its FIPS 203 (ML-KEM) or FIPS 204 (ML-DSA) replacement.{" "}
        {system.data.sarvamConfigured ? "The optional AI assistant (Sarvam sarvam-105b) can review a candidate, but its opinion never counts as verification." : "The optional AI reviewer is off: set SARVAM_API_KEY on the server to enable it."}
      </div>
      <Badge tone={system.data.sarvamConfigured ? "green" : "amber"}>{system.data.sarvamConfigured ? "AI reviewer configured" : "AI reviewer not configured"}</Badge>
    </div>
  );
}

// ---------------- AI Patch Studio ----------------
export function PatchStudio() {
  const { repoId, list, chosen, select } = usePatchSelection();
  const findings = useApi<FindingsResponse>(repoId ? `/api/repositories/${repoId}/findings` : null);
  const [error, setError] = React.useState<string | null>(null);
  if (!repoId) return <NoRepo />;
  const unpatched = findings.data?.findings.filter((f) => !f.patch) ?? [];

  return (
    <>
      <PageHeader
        title="AI Patch Studio"
        subtitle="Candidate cryptographic patches proposed for each finding. Proposals are only candidates: they reach the repository only after verification and a named human's approval."
      />
      <ProposerBanner />
      {error ? <div className="banner banner-error">{error}</div> : null}

      <Async res={list} empty={(d) => (d.length ? null : <Empty>No candidate patches yet.</Empty>)}>
        {(patches) => {
          const proposed = patches.filter((p) => p.status === "proposed").length;
          const approved = patches.filter((p) => p.status === "approved").length;
          const released = patches.filter((p) => p.status === "released").length;
          const rejected = patches.filter((p) => p.status === "rejected").length;

          const verified = patches.filter((p) => p.latestRun?.verdict === "verified_candidate").length;
          const failed = patches.filter((p) => p.latestRun?.verdict === "failed").length;
          const unverified = patches.filter((p) => !p.latestRun).length;

          const protocolScopeCount = patches.filter((p) => p.touchesProtocol).length;
          const internalScopeCount = patches.length - protocolScopeCount;

          const statusSegments = [
            { label: "Pending Review", value: proposed, color: "var(--cs-accent)" },
            { label: "Approved", value: approved, color: "var(--cs-green)" },
            { label: "Released", value: released, color: "var(--cs-blue)" },
            { label: "Rejected", value: rejected, color: "var(--cs-red)" },
          ].filter((s) => s.value > 0);

          const verificationSegments = [
            { label: "Verified Candidates", value: verified, color: "var(--cs-green)" },
            { label: "Unverified / Awaiting", value: unverified, color: "var(--cs-gold)" },
            { label: "Failed Checks", value: failed, color: "var(--cs-red)" },
          ].filter((s) => s.value > 0);

          return (
            <>
              {/* Visual Analytics Row */}
              <div className="grid grid-3" style={{ marginBottom: 24 }}>
                <Card title="Candidate Lifecycle Status">
                  <DonutChart
                    segments={statusSegments}
                    centerLabel="Patches"
                    centerValue={patches.length}
                  />
                </Card>

                <Card title="Verification Gate Readiness">
                  <DonutChart
                    segments={verificationSegments}
                    centerLabel="Verified"
                    centerValue={`${verified}/${patches.length}`}
                  />
                </Card>

                <Card title="Interbank Protocol Scope">
                  <div style={{ display: "grid", gap: 12 }}>
                    <p style={{ fontSize: 13, color: "var(--cs-text-2)", lineHeight: 1.5 }}>
                      Patches that touch interbank network protocols require simulated peer handshake verification before approval.
                    </p>
                    <BarChart
                      items={[
                        { label: "Touches Protocol (Interbank)", count: protocolScopeCount, color: "var(--cs-accent)", sub: "Handshake Req." },
                        { label: "Internal Service / Storage", count: internalScopeCount, color: "var(--cs-blue)", sub: "Local Diff" },
                      ]}
                    />
                  </div>
                </Card>
              </div>

              {/* Split Main View */}
              <div className="split split-picker">
                <div>
                  <Card title="Candidate Patch Registry">
                    <PatchPicker patches={patches} value={chosen?.id ?? ""} onChange={select} />
                  </Card>

                  {unpatched.length ? (
                    <Card title="Findings Awaiting Candidates">
                      <ul className="list small">
                        {unpatched.map((f) => (
                          <li key={f.id} style={{ justifyContent: "space-between", alignItems: "center" }}>
                            <span>
                              <span className="mono">{f.file}:{f.line}</span>
                              <div className="muted">{f.proposalBlocked || `${f.algorithm} usage`}</div>
                            </span>
                            {!f.proposalBlocked ? (
                              <button
                                className="btn btn-small btn-primary"
                                onClick={() => mutate(`/api/findings/${f.id}/propose`).catch((e: ApiError) => setError(e.message))}
                              >
                                Synthesize Patch
                              </button>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    </Card>
                  ) : null}
                </div>
                {chosen ? <PatchPanel patch={chosen} /> : null}
              </div>
            </>
          );
        }}
      </Async>
    </>
  );
}

function PatchPanel({ patch }: { patch: Patch }) {
  const [sarvam, setSarvam] = React.useState<{ model: string; analysis: string } | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [sarvamError, setSarvamError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setSarvam(null);
    setSarvamError(null);
  }, [patch.id]);

  const runAnalysis = async () => {
    setLoading(true);
    setSarvamError(null);
    try {
      const res = await mutate<{ ok: boolean; model: string; analysis: string }>(`/api/patches/${patch.id}/sarvam-analyze`);
      setSarvam(res);
    } catch (e) {
      setSarvamError((e as ApiError).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title={<span className="mono">{patch.file}:{patch.line}</span>} actions={<PatchBadge status={patch.status} />}>
      <dl className="fields" style={{ marginBottom: 14 }}>
        <Field label="Proposed change">{patch.fromAlgorithm} → {patch.algorithms.join(", ") || "SHA-256"}</Field>
        <Field label="Rationale">{patch.rationale}</Field>
        <Field label="Proposer engine">
          <span>{patch.proposer}</span>
        </Field>
        <Field label="Candidate patch hash">{mono(patch.hash.slice(0, 16))}</Field>
        <Field label="Original file hash">{mono(patch.baseHash.slice(0, 16))}</Field>
        <Field label="Protocol scope">{patch.touchesProtocol ? "Yes — peer negotiation handshake verification required" : "No — internal service"}</Field>
      </dl>

      {/* Sarvam AI Deep Reasoning & Assessment Box */}
      <div style={{ margin: "18px 0", padding: "16px 18px", borderRadius: 12, background: "rgba(254, 243, 199, 0.45)", border: "1.5px solid var(--cs-border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10, flexWrap: "wrap", gap: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 18 }}>🧠</span>
            <strong style={{ fontSize: 13.5, color: "var(--cs-text)" }}>Optional AI review (Sarvam sarvam-105b)</strong>
          </div>
          <button
            className="btn btn-small btn-primary"
            onClick={runAnalysis}
            disabled={loading}
          >
            {loading ? "Asking the AI reviewer…" : sarvam ? "Ask again" : "Ask the AI reviewer"}
          </button>
        </div>

        {sarvam ? (
          <div style={{ fontSize: 13, color: "var(--cs-text-2)", lineHeight: 1.65, marginTop: 8 }}>
            <p style={{ whiteSpace: "pre-line" }}>{sarvam.analysis}</p>
            <div style={{ marginTop: 10, fontSize: 11.5, color: "var(--cs-muted)" }}>
              Generated by <strong>{sarvam.model}</strong>. Advisory only: it is not a verification result and cannot unlock approval.
            </div>
          </div>
        ) : sarvamError ? (
          <div className="banner banner-error" style={{ margin: "8px 0 0", padding: "8px 12px", fontSize: 12.5 }}>
            {sarvamError}
          </div>
        ) : (
          <p style={{ fontSize: 12.5, color: "var(--cs-muted)", lineHeight: 1.5 }}>
            Sends this diff to Sarvam's hosted model for a second opinion on FIPS 203/204 alignment and harvest-now-decrypt-later exposure. Code leaves this server when you use it. Needs the engineer role and a configured API key.
          </p>
        )}
      </div>

      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--cs-text)", marginBottom: 6 }}>Unified Code Diff:</div>
        <Diff diff={patch.diff} />
      </div>
      <div className="kv" style={{ marginTop: 16 }}>
        <Link className="btn btn-primary" to={`/verification?patch=${patch.id}`}>Open in Verification Center & Run Checks →</Link>
      </div>
    </Card>
  );
}

// ---------------- Living Verification Center with Visual Charts & VerifyFigure ----------------
export function Verification() {
  const { repoId, list, chosen, select } = usePatchSelection(true);
  const checkpoints = useApi<Checkpoint[]>(repoId ? `/api/repositories/${repoId}/checkpoints` : null);
  if (!repoId) return <NoRepo />;

  return (
    <>
      <PageHeader
        title="Verification Center & Inspection Line"
        subtitle="Every check runs for real against throwaway baseline and candidate copies. A candidate patch advances along the inspection rail only as its actual test checks pass."
      />

      <Async res={list} empty={(d) => (d.length ? null : <Empty>No candidate patches to verify.</Empty>)}>
        {(patches) => (
          <div className="split split-picker">
            <div>
              <Card title="Candidate Patches Under Test">
                <PatchPicker patches={patches} value={chosen?.id ?? ""} onChange={select} />
              </Card>
            </div>
            {chosen ? (
              <VerificationPanel
                key={chosen.id}
                patch={chosen}
                checkpoint={checkpoints.data?.find((c) => c.patchId === chosen.id && c.status === "active") ?? null}
              />
            ) : null}
          </div>
        )}
      </Async>
    </>
  );
}

const ICON: Record<string, string> = { passed: "✓", failed: "✕", blocked: "✕", running: "…", unavailable: "!", not_applicable: "–", queued: "·", not_run: "·" };

function VerificationPanel({ patch, checkpoint }: { patch: Patch; checkpoint: Checkpoint | null }) {
  const detail = useApi<PatchDetail>(`/api/patches/${patch.id}`);
  const running = patch.latestRun?.status === "running";
  const run = useApi<Run>(patch.latestRun ? `/api/runs/${patch.latestRun.id}` : null, running ? 1000 : undefined);
  const r = patch.latestRun ? run.data : null;

  // Chart data from check statuses
  const checks = r?.checks ?? [];
  const passed = checks.filter((c) => c.status === "passed").length;
  const failed = checks.filter((c) => c.status === "failed" || c.status === "blocked").length;
  const runningChecks = checks.filter((c) => c.status === "running").length;
  const unavailable = checks.filter((c) => c.status === "unavailable").length;
  const notRun = checks.filter((c) => c.status === "not_run" || c.status === "queued").length;

  const checkSegments = [
    { label: "Passed Checks", value: passed, color: "var(--cs-green)" },
    { label: "Failed / Blocked", value: failed, color: "var(--cs-red)" },
    { label: "Running", value: runningChecks, color: "var(--cs-blue)" },
    { label: "Unavailable", value: unavailable, color: "var(--cs-gold)" },
    { label: "Not Run", value: notRun, color: "var(--cs-muted)" },
  ].filter((s) => s.value > 0);

  const passPct = checks.length > 0 ? Math.round((passed / checks.length) * 100) : 0;

  return (
    <div>
      {/* Visual Check Execution Donut Card */}
      {r ? (
        <div style={{ marginBottom: 20 }}>
          <div className="grid grid-2">
            <Card title="Check Results Breakdown">
              <DonutChart
                segments={checkSegments}
                centerLabel="Pass Rate"
                centerValue={`${passPct}%`}
              />
            </Card>
            <Card title="Empirical Verification Summary">
              <dl className="fields">
                <Field label="Run status"><VerdictBadge verdict={r.status === "running" ? "running" : r.verdict} /></Field>
                <Field label="Started at">{fmtTime(r.startedAt)}</Field>
                <Field label="Test execution host">{r.python ?? "Python not found"}</Field>
                <Field label="Total check steps">{checks.length} checks</Field>
                <Field label="Required checks passed">{passed} of {checks.filter((c) => c.required).length} required</Field>
              </dl>
            </Card>
          </div>
        </div>
      ) : null}

      {/* Living Embedded VerifyFigure */}
      <div style={{ marginBottom: 20 }}>
        <Card
          title={
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span>Living Inspection Carriage:</span>
              <span className="mono" style={{ fontSize: 12 }}>{patch.file}:{patch.line}</span>
            </div>
          }
          actions={<VerdictBadge verdict={r ? (r.status === "running" ? "running" : r.verdict) : "not_run"} />}
        >
          <p style={{ fontSize: 13, color: "var(--cs-text-2)", marginBottom: 14 }}>
            The physical inspection carriage advances along the rail and halts at the first failing or unrun station. Click any station or carriage component to inspect check evidence.
          </p>
          <VerifyFigure patch={patch} run={r} checkpoint={checkpoint} />
        </Card>
      </div>

      {/* Verification Checklist */}
      <Card
        title="Check Execution Results"
        actions={<VerdictBadge verdict={r ? (r.status === "running" ? "running" : r.verdict) : "not_run"} />}
      >
        {!r ? (
          <Empty>This patch has not been verified yet. Click "Run verification" below to test the candidate against the baseline.</Empty>
        ) : (
          <>
            <p className="small muted" style={{ marginBottom: 12 }}>
              Run ID {mono(r.id)} · Started {fmtTime(r.startedAt)} · Test Engine: {r.python ?? "Python not found on backend host"}
            </p>
            <ol className="list checklist">
              {r.checks.map((c) => (
                <li key={c.id}>
                  <span className="check-icon" data-s={c.status} aria-hidden="true">{ICON[c.status]}</span>
                  <strong>{c.name} {c.required ? null : <span className="muted small">(optional)</span>}</strong>
                  <CheckBadge status={c.status} />
                  <div className="detail">
                    {c.detail}
                    {c.note ? <div className="muted">{c.note}</div> : null}
                    {c.output ? (
                      <details style={{ marginTop: 6 }}>
                        <summary style={{ cursor: "pointer", color: "var(--cs-accent-strong)" }}>View Check Stdout/Stderr</summary>
                        <pre className="code" style={{ maxHeight: 240, padding: "8px 12px", marginTop: 6 }}>{c.output}</pre>
                      </details>
                    ) : null}
                  </div>
                </li>
              ))}
            </ol>
            {r.verdict === "verified_candidate" ? (
              <p className="note" style={{ marginTop: 14 }}>
                <strong>Verified Candidate:</strong> Every configured required check passed without regression. This serves as verified empirical evidence for human review, not absolute mathematical proof.
              </p>
            ) : r.verdict === "failed" ? (
              <p className="note" style={{ marginTop: 14, borderColor: "rgba(225,29,72,0.3)", background: "var(--cs-red-bg)", color: "#9f1239" }}>
                <strong>Required Check Failed:</strong> The candidate patch cannot be approved or released. Review output, reject the patch, or propose a revision.
              </p>
            ) : null}
          </>
        )}
      </Card>

      <Card title="Human Review Gate">
        <ReviewActions patch={patch} checkpointId={checkpoint?.id ?? null} />
      </Card>

      {detail.data?.runs.length ? (
        <Card title="Run Execution History">
          <ul className="list small">
            {detail.data.runs.map((x) => (
              <li key={x.id} style={{ justifyContent: "space-between" }}>
                <span>
                  <span className="mono">{x.id}</span> <span className="muted">started {fmtTime(x.startedAt)}</span>
                </span>
                <VerdictBadge verdict={x.status === "running" ? "running" : x.verdict} />
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
    </div>
  );
}

// ---------------- Protocol Traces ----------------
export function Traces() {
  const { repoId } = useApp();
  const res = useApi<TraceRecord[]>(repoId ? `/api/repositories/${repoId}/traces` : null);
  if (!repoId) return <NoRepo />;
  return (
    <>
      <PageHeader
        title="Protocol Traces & Handshake Differential"
        subtitle="Handshake events from the repository's peer negotiation model (tools/negotiate.py), recorded during each verification run for baseline and candidate."
      />
      <Async res={res} empty={(d) => (d.length ? null : <Empty>No protocol traces yet. Traces are captured when a verification run executes the protocol compatibility check.</Empty>)}>
        {(list) => (
          <div className="grid">
            {list.map((t) => (
              <Card
                key={t.runId}
                title={<span className="mono">{t.file}:{t.line}</span>}
                actions={
                  <div className="kv">
                    <span className="small muted">{fmtTime(t.at)}</span>
                    <VerdictBadge verdict={t.verdict} />
                  </div>
                }
              >
                <TraceCompare traces={t.traces} compact />
              </Card>
            ))}
          </div>
        )}
      </Async>
    </>
  );
}

// ---------------- Rollback & Recovery ----------------
export function Rollback() {
  const { repoId } = useApp();
  const { can } = useAuth();
  const res = useApi<Checkpoint[]>(repoId ? `/api/repositories/${repoId}/checkpoints` : null);
  const [error, setError] = React.useState<string | null>(null);
  if (!repoId) return <NoRepo />;
  return (
    <>
      <PageHeader
        title="Rollback & Recovery Ledger"
        subtitle="Every release automatically stores the original file and cryptographic hashes. Rollback restores the original byte for byte, refusing if subsequent unverified mutations occurred."
      />
      {error ? <div className="banner banner-error">Backend refused: {error}</div> : null}
      <Async res={res} empty={(d) => (d.length ? null : <Empty>No checkpoints yet. A checkpoint is automatically minted when an approved patch is released.</Empty>)}>
        {(list) => (
          <Card>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Released At</th>
                    <th className="hide-sm">Original → Released Hash</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((c) => (
                    <tr key={c.id}>
                      <td className="mono"><strong>{c.file}</strong></td>
                      <td>{fmtTime(c.createdAt)}</td>
                      <td className="mono hide-sm small">{c.originalHash.slice(0, 12)} → {c.releasedHash.slice(0, 12)}</td>
                      <td>{c.status === "active" ? <Badge tone="blue">Active in Repo</Badge> : <Badge>Restored {fmtTime(c.restoredAt)}</Badge>}</td>
                      <td>
                        {c.status === "active" && can("reviewer") ? (
                          <button
                            className="btn btn-small btn-danger"
                            onClick={() => mutate(`/api/checkpoints/${c.id}/rollback`).catch((e: ApiError) => setError(e.message))}
                          >
                            Roll back byte-for-byte
                          </button>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </Async>
    </>
  );
}

// ---------------- Reports & Audit ----------------
function AuditIntegrity() {
  const v = useApi<AuditVerification>("/api/audit/verify");
  const [copied, setCopied] = React.useState(false);
  return (
    <Card title="Audit log integrity" actions={<button className="btn btn-small" onClick={v.reload} disabled={v.loading}>{v.loading ? "Checking…" : "Re-check now"}</button>}>
      <Async res={v}>
        {(r) => (
          <div className={r.ok ? "integrity integrity-ok" : "integrity integrity-bad"} role="status">
            <span className="integrity-mark" aria-hidden="true">{r.ok ? "✓" : "!"}</span>
            <div>
              <strong>{r.ok ? `Chain intact: all ${r.entries} entries verified` : `Tampering detected at entry #${r.brokenAt}`}</strong>
              <p className="small muted">
                {r.ok
                  ? "Every entry is HMAC-linked to the one before it, so editing, deleting or reordering any entry breaks the chain."
                  : `${r.reason}. Entries from #${r.brokenAt} on cannot be trusted. Restore audit.log from a backup and investigate who had access to the server.`}{" "}
                Checked {fmtTime(r.checkedAt)}.
              </p>
              {r.ok && r.head ? (
                <p className="small">
                  Chain head <code className="mono">{r.head.slice(0, 24)}…</code>{" "}
                  <button
                    className="btn btn-small btn-ghost"
                    onClick={() => {
                      void navigator.clipboard?.writeText(r.head!).then(() => setCopied(true));
                    }}
                  >
                    {copied ? "Copied" : "Copy full hash"}
                  </button>
                  <br />
                  <span className="muted">Paste it into a ticket or email now and then: if the log is ever cut short, the old head will no longer match.</span>
                </p>
              ) : null}
            </div>
          </div>
        )}
      </Async>
    </Card>
  );
}

export function Reports() {
  const { repoId } = useApp();
  const [page, setPage] = React.useState(0);
  const PAGE = 50;
  const audit = useApi<AuditList>(`/api/audit?limit=${PAGE}&offset=${page * PAGE}`);
  const findings = useApi<FindingsResponse>(repoId ? `/api/repositories/${repoId}/findings` : null);
  const plan = useApi<Plan>(repoId ? `/api/repositories/${repoId}/plan` : null);
  const patches = useApi<Patch[]>(repoId ? `/api/repositories/${repoId}/patches` : null);
  const [error, setError] = React.useState<string | null>(null);

  const download = async () => {
    try {
      const fullAudit = await api<AuditList>("/api/audit?limit=500");
      const verification = await api<AuditVerification>("/api/audit/verify");
      const report = {
        generatedAt: new Date().toISOString(),
        repository: repoId,
        scan: findings.data?.scan,
        findings: findings.data?.findings.map((f) => ({ id: f.id, algorithm: f.algorithm, file: f.file, line: f.line, role: f.role, risk: f.risk, deadline: f.deadline, recommendation: f.recommendation, verification: f.verification })),
        plan: plan.data,
        patches: patches.data?.map((p) => ({ id: p.id, file: p.file, line: p.line, status: p.status, verdict: p.latestRun?.verdict ?? null, verificationStartedBy: p.latestRun?.startedBy ?? null, decisions: p.decisions })),
        audit: { integrity: verification, entries: fullAudit.entries },
      };
      const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
      const a = Object.assign(document.createElement("a"), { href: url, download: `cryptoshift-${repoId}-report.json` });
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError((e as ApiError).message);
    }
  };

  const total = audit.data?.total ?? 0;
  return (
    <>
      <PageHeader
        title="Reports & Audit Log"
        subtitle="Every sign-in, scan, verification run, decision, release and rollback, under the account that did it. Export the inventory as a standard CycloneDX CBOM for other tools."
        actions={
          <div className="kv">
            <button className="btn" disabled={!repoId} onClick={() => repoId && downloadJson(`/api/repositories/${repoId}/cbom`, `${repoId}-cbom.cdx.json`).catch((e: ApiError) => setError(e.message))}>
              Export CBOM (CycloneDX 1.6)
            </button>
            <button className="btn btn-primary" disabled={!findings.data || !plan.data || !patches.data} onClick={() => void download()}>
              Download full report
            </button>
          </div>
        }
      />
      {error ? <div className="banner banner-error" role="alert">{error}</div> : null}
      <AuditIntegrity />
      <Async res={audit} empty={(d) => (d.entries.length ? null : <Empty>No audit events recorded yet.</Empty>)}>
        {(list) => (
          <Card title={`Audit log · ${total} entries`}>
            <div className="table-wrap" tabIndex={0} role="region" aria-label="Audit log table (scrolls sideways on small screens)">
              <table>
                <caption className="sr-only">Audit log, newest first</caption>
                <thead>
                  <tr>
                    <th scope="col">#</th>
                    <th scope="col">When</th>
                    <th scope="col">Account</th>
                    <th scope="col">Action</th>
                    <th scope="col">Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {list.entries.map((a) => (
                    <tr key={a.id}>
                      <td className="mono small">{a.seq}</td>
                      <td style={{ whiteSpace: "nowrap" }}>{fmtTime(a.at)}</td>
                      <td>
                        <strong>{a.actor}</strong>
                        {a.legacy ? <Badge tone="amber">imported</Badge> : null}
                      </td>
                      <td className="mono" style={{ whiteSpace: "nowrap" }}>{a.action}</td>
                      <td>{a.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="kv" style={{ marginTop: 12, justifyContent: "space-between" }}>
              <span className="small muted">
                Showing {page * PAGE + 1}–{Math.min(total, (page + 1) * PAGE)} of {total}. Entries marked “imported” came from the old unprotected log and cannot be proven.
              </span>
              <span className="kv">
                <button className="btn btn-small" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>Newer</button>
                <button className="btn btn-small" disabled={(page + 1) * PAGE >= total} onClick={() => setPage((p) => p + 1)}>Older</button>
              </span>
            </div>
          </Card>
        )}
      </Async>
    </>
  );
}

// ---------------- Settings: account, team, system ----------------
function PasswordForm() {
  const { passwordMin } = useAuth();
  const [form, setForm] = React.useState({ current: "", next: "", confirm: "" });
  const [msg, setMsg] = React.useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = React.useState(false);
  return (
    <form
      className="stack"
      onSubmit={async (e) => {
        e.preventDefault();
        if (form.next !== form.confirm) return setMsg({ ok: false, text: "The new passwords do not match" });
        setBusy(true);
        try {
          await mutate("/api/auth/password", { current: form.current, next: form.next });
          setForm({ current: "", next: "", confirm: "" });
          setMsg({ ok: true, text: "Password changed. Other devices were signed out." });
        } catch (err) {
          setMsg({ ok: false, text: (err as ApiError).message });
        } finally {
          setBusy(false);
        }
      }}
    >
      <div className="form-row">
        <label htmlFor="pw-current">Current password</label>
        <input id="pw-current" type="password" autoComplete="current-password" required value={form.current} onChange={(e) => setForm({ ...form, current: e.target.value })} />
      </div>
      <div className="form-row">
        <label htmlFor="pw-next">New password <span className="small muted">({passwordMin}+ characters)</span></label>
        <input id="pw-next" type="password" autoComplete="new-password" minLength={passwordMin} required value={form.next} onChange={(e) => setForm({ ...form, next: e.target.value })} />
      </div>
      <div className="form-row">
        <label htmlFor="pw-confirm">Confirm new password</label>
        <input id="pw-confirm" type="password" autoComplete="new-password" required value={form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.value })} />
      </div>
      <div className="kv">
        <button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : "Change password"}</button>
        {msg ? <span className={msg.ok ? "small" : "small text-danger"} role={msg.ok ? "status" : "alert"}>{msg.text}</span> : null}
      </div>
    </form>
  );
}

const ROLES: Role[] = ["viewer", "engineer", "reviewer", "admin"];

function TeamCard() {
  const { user: me } = useAuth();
  const users = useApi<User[]>("/api/users");
  const [form, setForm] = React.useState({ username: "", displayName: "", role: "engineer" as Role, password: "" });
  const [msg, setMsg] = React.useState<{ ok: boolean; text: string } | null>(null);
  const update = (u: User, body: { role?: Role; disabled?: boolean }) =>
    mutate(`/api/users/${u.id}`, body)
      .then(() => setMsg({ ok: true, text: `Updated @${u.username}` }))
      .catch((e: ApiError) => setMsg({ ok: false, text: e.message }));
  return (
    <Card title="Team accounts" actions={<Badge tone="blue">Administrator</Badge>}>
      <p className="small muted" style={{ marginBottom: 12 }}>
        Four-eyes needs at least two reviewers: the person who runs verification cannot approve the same patch.
      </p>
      <Async res={users}>
        {(list) => (
          <div className="table-wrap">
            <table>
              <caption className="sr-only">Accounts</caption>
              <thead>
                <tr>
                  <th scope="col">Account</th>
                  <th scope="col">Role</th>
                  <th scope="col" className="hide-sm">Last sign-in</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {list.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <strong>{u.displayName}</strong>
                      <div className="small muted">@{u.username}{u.id === me?.id ? " (you)" : ""}</div>
                    </td>
                    <td>
                      <label className="sr-only" htmlFor={`role-${u.id}`}>Role for {u.username}</label>
                      <select id={`role-${u.id}`} className="select" value={u.role} onChange={(e) => void update(u, { role: e.target.value as Role })}>
                        {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
                      </select>
                    </td>
                    <td className="hide-sm small">{u.lastLoginAt ? fmtTime(u.lastLoginAt) : "Never"}</td>
                    <td>
                      {u.id === me?.id ? (
                        <Badge tone="green">Active</Badge>
                      ) : (
                        <button className={u.disabled ? "btn btn-small" : "btn btn-small btn-danger"} onClick={() => void update(u, { disabled: !u.disabled })}>
                          {u.disabled ? "Re-enable" : "Disable"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Async>
      <form
        className="team-add"
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            const u = await mutate<User>("/api/users", form);
            setMsg({ ok: true, text: `Created @${u.username}. Share the temporary password with them in person or over a secure channel; they should change it after signing in.` });
            setForm({ username: "", displayName: "", role: "engineer", password: "" });
          } catch (err) {
            setMsg({ ok: false, text: (err as ApiError).message });
          }
        }}
      >
        <strong className="small">Add a teammate</strong>
        <div className="team-add-grid">
          <input aria-label="Username" placeholder="username" autoCapitalize="none" spellCheck={false} required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
          <input aria-label="Display name" placeholder="Display name" value={form.displayName} onChange={(e) => setForm({ ...form, displayName: e.target.value })} />
          <select aria-label="Role" className="select" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
            {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
          </select>
          <input aria-label="Temporary password" type="password" autoComplete="new-password" placeholder="Temporary password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          <button className="btn btn-primary">Add</button>
        </div>
        <p className="small muted">{ROLE_CAN[form.role]}.</p>
      </form>
      {msg ? <div className={msg.ok ? "state small" : "state state-error small"} role={msg.ok ? "status" : "alert"}>{msg.text}</div> : null}
    </Card>
  );
}

export function Settings() {
  const { user, can } = useAuth();
  const system = useApi<SystemInfo>("/api/system");
  const [msg, setMsg] = React.useState<string | null>(null);
  if (!user) return null;
  return (
    <>
      <PageHeader title="Account & Settings" subtitle="Your identity, your team, and the server that runs verification." />
      <div className="grid grid-2">
        <Card title="Your account">
          <dl className="fields" style={{ marginBottom: 16 }}>
            <Field label="Name on approvals">{user.displayName}</Field>
            <Field label="Username">@{user.username}</Field>
            <Field label="Role">
              <Badge tone="blue">{ROLE_LABEL[user.role]}</Badge> <span className="small muted">{ROLE_CAN[user.role]}</span>
            </Field>
          </dl>
          {user.mustChangePassword ? <div className="banner banner-info">An administrator set your password. Choose your own now.</div> : null}
          <PasswordForm />
        </Card>
        <Card title="Verification server">
          <Async res={system}>
            {(h) => (
              <dl className="fields">
                <Field label="CryptoShift version">{h.version}</Field>
                <Field label="Server started">{fmtTime(h.startedAt)}</Field>
                <Field label="Node.js">{h.node}</Field>
                <Field label="Python for tests">{h.python ?? <Badge tone="amber">Not found: verification checks will report “unavailable”</Badge>}</Field>
                <Field label="Patch proposer">{h.proposer}</Field>
                <Field label="AI reviewer">{h.sarvamConfigured ? <Badge tone="green">Configured</Badge> : <Badge>Not configured</Badge>}</Field>
                <Field label="Parallel verification runs">{h.maxConcurrentRuns}</Field>
              </dl>
            )}
          </Async>
          {can("admin") ? (
            <div className="kv" style={{ marginTop: 16 }}>
              <button
                className="btn btn-danger"
                onClick={async () => {
                  if (!confirm("Reset demo state? Working copies, patches, runs and checkpoints are cleared. Accounts and the audit log are kept.")) return;
                  try {
                    await mutate("/api/admin/reset-state");
                    setMsg("Demo state reset. The reset itself is in the audit log.");
                  } catch (e) {
                    setMsg((e as ApiError).message);
                  }
                }}
              >
                Reset demo state
              </button>
              {msg ? <span className="small muted" role="status">{msg}</span> : null}
            </div>
          ) : null}
        </Card>
      </div>
      {can("admin") ? <TeamCard /> : null}
    </>
  );
}
