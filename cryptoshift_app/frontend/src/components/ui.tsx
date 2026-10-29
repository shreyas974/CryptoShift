import * as React from "react";
import type { ApiError } from "../api/client";
import type { CheckStatus, Finding, Verdict, Basis, PatchStatus } from "../api/types";

export type Tone = "green" | "amber" | "red" | "grey" | "blue" | "orange";

export function Badge({ tone = "grey", children, title }: { tone?: Tone; children: React.ReactNode; title?: string }) {
  return (
    <span className={`badge badge-${tone}`} title={title}>
      {children}
    </span>
  );
}

const CHECK: Record<CheckStatus, [Tone, string]> = {
  passed: ["green", "Passed"],
  failed: ["red", "Failed"],
  blocked: ["red", "Blocked"],
  running: ["blue", "Running"],
  queued: ["grey", "Queued"],
  unavailable: ["amber", "Unavailable"],
  not_applicable: ["grey", "Not applicable"],
  not_run: ["grey", "Not run"],
};
export const CheckBadge = ({ status }: { status: CheckStatus }) => <Badge tone={CHECK[status][0]}>{CHECK[status][1]}</Badge>;

export function VerdictBadge({ verdict, running }: { verdict: Verdict | "not_run" | "no_patch" | "running" | undefined; running?: boolean }) {
  if (running || verdict === "running") return <Badge tone="blue">Running</Badge>;
  if (verdict === "verified_candidate") return <Badge tone="green" title="Every configured required check passed. Not a proof of absolute security.">Verified candidate</Badge>;
  if (verdict === "failed") return <Badge tone="red">Failed</Badge>;
  if (verdict === "incomplete") return <Badge tone="amber">Incomplete</Badge>;
  if (verdict === "error") return <Badge tone="red">Runner error</Badge>;
  if (verdict === "no_patch") return <Badge tone="grey">No patch</Badge>;
  return <Badge tone="grey">Not run</Badge>;
}

const PATCH: Record<PatchStatus, [Tone, string]> = {
  proposed: ["amber", "Pending review"],
  approved: ["green", "Approved"],
  rejected: ["red", "Rejected"],
  released: ["blue", "Released"],
  rolled_back: ["grey", "Rolled back"],
};
export const PatchBadge = ({ status }: { status: PatchStatus }) => <Badge tone={PATCH[status][0]}>{PATCH[status][1]}</Badge>;

export const BASIS_LABEL: Record<Basis, string> = { declared: "Declared", inferred: "Inferred", unknown: "Unknown" };
export const BasisBadge = ({ basis }: { basis: Basis }) => <Badge tone={basis === "declared" ? "green" : basis === "inferred" ? "amber" : "grey"}>{BASIS_LABEL[basis]}</Badge>;

export function RiskBadge({ risk }: { risk: Finding["risk"] }) {
  const tone: Tone = risk.band === "critical" ? "red" : risk.band === "high" ? "orange" : risk.band === "medium" ? "amber" : "green";
  return (
    <span className="risk">
      <span className="risk-bar" aria-hidden="true">
        <span style={{ width: `${risk.score}%` }} data-band={risk.band} />
      </span>
      <Badge tone={tone}>
        {risk.score} · {risk.band}
      </Badge>
    </span>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle ? <p className="muted">{subtitle}</p> : null}
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  );
}

export function Card({ title, actions, children, className }: { title?: React.ReactNode; actions?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={className ? `card ${className}` : "card"}>
      {title || actions ? (
        <div className="card-head">
          {title ? <h2>{title}</h2> : <span />}
          {actions}
        </div>
      ) : null}
      {children}
    </section>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="state state-loading" role="status">
      <span className="spinner" aria-hidden="true" />
      {label}…
    </div>
  );
}

export function ErrorState({ error, retry }: { error: ApiError | Error; retry?: () => void }) {
  return (
    <div className="state state-error" role="alert">
      <strong>Could not load data.</strong> {error.message}
      {retry ? (
        <button className="btn btn-small" onClick={retry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="state state-empty">{children}</div>;
}

/** Render a resource with honest loading / error / empty handling. */
export function Async<T>({ res, empty, children }: { res: { data: T | null; error: ApiError | null; loading: boolean; reload: () => void }; empty?: (data: T) => React.ReactNode | null; children: (data: T) => React.ReactNode }) {
  if (res.error && !res.data) return <ErrorState error={res.error} retry={res.reload} />;
  if (!res.data) return <Loading />;
  const none = empty?.(res.data);
  return (
    <>
      {res.error ? <ErrorState error={res.error} retry={res.reload} /> : null}
      {none ?? children(res.data)}
    </>
  );
}

export function Code({ lines, highlight }: { lines: { line: number; text: string }[]; highlight?: number }) {
  return (
    <pre className="code" tabIndex={0}>
      {lines.map((l) => (
        <div key={l.line} className={l.line === highlight ? "code-line code-hit" : "code-line"}>
          <span className="code-num">{l.line}</span>
          <code>{l.text || " "}</code>
        </div>
      ))}
    </pre>
  );
}

export function Diff({ diff }: { diff: string }) {
  return (
    <pre className="code diff" tabIndex={0} aria-label="Unified diff">
      {diff.split("\n").map((line, i) => {
        const kind = line.startsWith("+++") || line.startsWith("---") ? "meta" : line.startsWith("@@") ? "hunk" : line.startsWith("+") ? "add" : line.startsWith("-") ? "del" : "ctx";
        return (
          <div key={i} className={`diff-${kind}`}>
            <code>{line || " "}</code>
          </div>
        );
      })}
    </pre>
  );
}

export function SearchBox({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <label className="search">
      <span className="sr-only">{placeholder}</span>
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <circle cx="7" cy="7" r="4.5" />
        <path d="M10.5 10.5 14 14" />
      </svg>
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
    </label>
  );
}

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="field">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

export const mono = (text: React.ReactNode) => <code className="mono">{text}</code>;

export const fmtTime = (iso: string | null | undefined) => (iso ? new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "—");
