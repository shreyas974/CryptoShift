import type { ReactNode } from "react";
import type { Source } from "../api/client";
import { badgeInfo, plainText } from "../lib/status";
import { useEvidence } from "./evidence";

/** Status badge: icon + text + colour (never colour alone). */
export function Badge({ value, title }: { value: unknown; title?: string }) {
  const b = badgeInfo(value);
  return (
    <span className={`badge t-${b.tone}`} title={title ?? b.meaning} data-status={b.status}>
      <span aria-hidden="true">{b.icon}</span>
      {b.status}
    </span>
  );
}

export function Card({
  title,
  children,
  className = "",
  actions,
}: {
  title?: ReactNode;
  children: ReactNode;
  className?: string;
  actions?: ReactNode;
}) {
  return (
    <section className={`glass glass-card lift p-4 ${className}`}>
      {(title || actions) && (
        <header className="mb-3 flex items-center gap-2">
          {title && <h2 className="m-0 text-lg font-semibold">{title}</h2>}
          <span className="flex-1" />
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

/** A number that opens the evidence drawer for its source. */
export function Evidence({
  source,
  children,
  label,
}: {
  source: Source | undefined;
  children: ReactNode;
  label: string;
}) {
  const open = useEvidence();
  if (!source) return <>{children}</>;
  return (
    <span className="inline-flex items-baseline gap-1">
      {children}
      <button
        type="button"
        className="t-info cursor-pointer border-0 bg-transparent text-sm"
        aria-label={`Evidence for ${label}`}
        onClick={() => open(source, label)}
      >
        ⓘ
      </button>
    </span>
  );
}

export function Kpi({
  label,
  value,
  note,
  source,
}: {
  label: string;
  value: ReactNode;
  note?: string;
  source?: Source;
}) {
  return (
    <Card>
      <div className="t-muted text-xs font-semibold tracking-widest uppercase">{label}</div>
      <div className="mono mt-1 text-3xl font-semibold">
        <Evidence source={source} label={label}>
          {value}
        </Evidence>
      </div>
      {note && <div className="t-muted mt-1 text-sm">{note}</div>}
    </Card>
  );
}

/** Text that came from scanned files: shown as plain, capped text in a code element. */
export function ScannedText({ value, limit = 160 }: { value: unknown; limit?: number }) {
  return <code className="text-sm break-all whitespace-pre-wrap">{plainText(value, limit)}</code>;
}

export function StatusCard({ status, source }: { status: string; source?: Source }) {
  if (status === "ok") return null;
  const what =
    status === "missing" ? "File missing" : status === "schema_mismatch" ? "Schema mismatch" : "Could not read file";
  return (
    <div role="alert" className="glass t-warn mb-4 p-4">
      <strong>{what}:</strong> <code>{source?.file}</code>
      {source?.command && (
        <div className="t-muted mt-1 text-sm">
          Produce it with <code>{source.command}</code>
        </div>
      )}
    </div>
  );
}

export function Notice({ children, tone = "warn" }: { children: ReactNode; tone?: "warn" | "info" | "bad" | "sim" }) {
  return (
    <div className={`glass mb-4 border-l-4 p-3 text-sm`} style={{ borderLeftColor: `var(--${tone})` }} role="note">
      {children}
    </div>
  );
}

export function Loading({ what }: { what: string }) {
  return (
    <div role="status" aria-live="polite" className="t-muted p-6">
      Loading {what}…
    </div>
  );
}

export function ErrorState({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : "unknown error";
  return (
    <div role="alert" className="glass t-bad p-4">
      Could not load data: {plainText(msg, 300)}
    </div>
  );
}

export function SourceFooter({ sources }: { sources: (Source | undefined)[] }) {
  return (
    <footer className="t-muted mt-6 text-xs">
      {sources
        .filter((s): s is Source => Boolean(s))
        .map((s) => (
          <div key={s.file}>
            Source: <code>{s.file}</code> · modified {s.modified ?? "n/a"} · producer {s.producer} · label: {s.label}
          </div>
        ))}
      <div className="mt-1">
        Background is a decorative illustration. QpiAI QCloud results shown are simulator runs.
      </div>
    </footer>
  );
}

/** Small accessible bar chart with a data table ("Data behind this chart"). */
export function BarList({
  title,
  rows,
  max,
}: {
  title: string;
  rows: { label: string; value: number; tone?: string }[];
  max?: number;
}) {
  const top = max ?? Math.max(1, ...rows.map((r) => r.value));
  return (
    <figure className="m-0">
      <figcaption className="t-muted mb-2 text-sm">{title}</figcaption>
      <div className="flex flex-col gap-2" aria-hidden="true">
        {rows.map((r) => (
          <div key={r.label} className="grid grid-cols-[minmax(120px,40%)_1fr_auto] items-center gap-2 text-sm">
            <span className="truncate">{r.label}</span>
            <span
              className="h-3 rounded"
              style={{ width: `${(100 * r.value) / top}%`, background: `var(--${r.tone ?? "accent"})`, minWidth: 2 }}
            />
            <span className="mono">{r.value}</span>
          </div>
        ))}
      </div>
      <details className="mt-2 text-sm">
        <summary className="cursor-pointer">Data behind this chart</summary>
        <table className="dtable">
          <tbody>
            {rows.map((r) => (
              <tr key={r.label}>
                <th scope="row">{r.label}</th>
                <td className="num">{r.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
