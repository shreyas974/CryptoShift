import * as React from "react";
import { Link } from "react-router-dom";
import { AnatomyFrame, type PartInfo } from "../../anatomy/AnatomyFrame";
import { useLoop, follow } from "../../anatomy/kit/react/live";
import { CabinetBody, Drawer, RiskDial, SLOTS, W, H, anchorFor, PULL_DISTANCE, assetKeys, PipLegend } from "./AssetArt";
import { Part } from "../../anatomy/parts";
import { fieldsOf, type FieldId } from "./model";
import type { Finding } from "../../api/types";
import { BasisBadge, Badge, Code, RiskBadge, VerdictBadge, Field, mono } from "../../components/ui";
import { FileViewer } from "../../components/FileViewer";

const STATIC_ART = (
  <g key="static">
    <CabinetBody />
  </g>
);

export function AssetFigure({ finding, toolbar }: { finding: Finding; toolbar?: React.ReactNode }) {
  const fields = React.useMemo(() => fieldsOf(finding), [finding]);
  const [selected, setSelected] = React.useState<FieldId | null>("evidence");
  const [viewer, setViewer] = React.useState(false);
  const target = React.useRef<Record<string, number>>({});
  const [ext, setExt] = React.useState<Record<string, number>>({});
  const shown = React.useRef<Record<string, number>>({});
  const [last, setLast] = React.useState<FieldId | null>(selected);

  const kick = useLoop((dt, calm) => {
    let moving = false;
    const next: Record<string, number> = {};
    for (const s of SLOTS) {
      const goal = target.current[s.id] ?? 0;
      const now = follow(shown.current[s.id] ?? 0, goal, dt, 0.16, calm);
      next[s.id] = now;
      if (now !== goal) moving = true;
    }
    shown.current = next;
    setExt(next);
    return moving;
  }, false);

  // Declared after useLoop so the kit's mount effect cannot cancel the first kick.
  React.useEffect(() => {
    target.current = Object.fromEntries(SLOTS.map((s) => [s.id, s.id === selected ? PULL_DISTANCE : 0]));
    if (selected) setLast(selected);
    kick();
  }, [selected, kick]);

  const parts: PartInfo[] = fields.map((f) => ({
    id: f.id,
    label: f.label,
    summary: f.summary,
    readout: f.readout,
    status: f.status,
    statusLabel: f.statusLabel,
    anchor: anchorFor(f.id, (ext[f.id] ?? 0) > PULL_DISTANCE / 2),
  }));
  const byId = new Map(fields.map((f) => [f.id, f]));
  // Back column first, lower rows first; the open (or closing) drawer is painted last.
  const order = [...SLOTS].sort((a, b) => (a.id === last ? 1 : b.id === last ? -1 : a.col - b.col || b.row - a.row));
  const current = selected ? byId.get(selected)! : null;
  const score = finding.risk.score;

  return (
    <>
      <AnatomyFrame
        fig="Fig 02"
        title="Cryptographic asset"
        ariaLabel={`Evidence cabinet for ${finding.algorithm} at ${finding.file} line ${finding.line}`}
        width={W}
        height={H}
        parts={parts}
        selected={selected}
        onSelect={(id) => setSelected(id as FieldId | null)}
        idleReadout={`${finding.algorithm} · risk ${score}`}
        hint="Pull a drawer"
        keys={assetKeys}
        caption={
          <>
            <PipLegend />
            <span>
              Every drawer is read from scan finding <code>{finding.id}</code> of <code>{finding.repo}</code>. Unknown fields stay empty; nothing is filled in by the figure.
            </span>
          </>
        }
        toolbar={toolbar}
        detail={current ? <FieldDetail id={current.id} finding={finding} onOpenFile={() => setViewer(true)} /> : <p className="muted">Select a drawer or a component in the list to inspect that field.</p>}
      >
        {STATIC_ART}
        <Part id="risk">
          <RiskDial score={score} />
        </Part>
        {order.map((s) => (
          <Drawer key={s.id} slot={s} field={byId.get(s.id) ?? null} extension={ext[s.id] ?? 0} />
        ))}
        {/* the dial is also the risk drawer's instrument: selecting either highlights both */}
      </AnatomyFrame>
      {viewer ? <FileViewer repo={finding.repo} path={finding.file} line={finding.line} onClose={() => setViewer(false)} /> : null}
    </>
  );
}

function FieldDetail({ id, finding: f, onOpenFile }: { id: FieldId; finding: Finding; onOpenFile: () => void }) {
  const head = (title: string, badge: React.ReactNode) => (
    <div className="kv" style={{ justifyContent: "space-between" }}>
      <h3>{title}</h3>
      {badge}
    </div>
  );
  switch (id) {
    case "repository":
      return (
        <>
          {head("Repository", <BasisBadge basis="declared" />)}
          <dl className="fields">
            <Field label="Repository">{mono(f.repo)}</Field>
            <Field label="Finding id">{mono(f.id)}</Field>
            <Field label="Scanner rule">{mono(f.rule)}</Field>
          </dl>
          <Link to="/repositories" className="btn btn-small">Repository details</Link>
        </>
      );
    case "evidence":
      return (
        <>
          {head("File and line evidence", <BasisBadge basis="declared" />)}
          <p className="mono">{f.file}:{f.line}:{f.column}</p>
          <Code lines={f.excerpt} highlight={f.line} />
          {f.usages.length ? (
            <p className="small muted">
              Also referenced on line{f.usages.length > 1 ? "s" : ""} {f.usages.map((u) => `${u.line}${u.fn ? ` (${u.fn})` : ""}`).join(", ")}.
            </p>
          ) : null}
          <button className="btn btn-primary btn-small" onClick={onOpenFile}>
            Open {f.file.split("/").pop()} at line {f.line}
          </button>
        </>
      );
    case "algorithm":
      return (
        <>
          {head("Algorithm / API", <BasisBadge basis="declared" />)}
          <dl className="fields">
            <Field label="Algorithm">{mono(f.algorithm)}</Field>
            <Field label="API">{mono(f.api)}</Field>
            <Field label="Key size">{f.keyBits ? `${f.keyBits} bits` : "—"}</Field>
            <Field label="Quantum threat">{f.threat.label}</Field>
          </dl>
        </>
      );
    case "role":
      return (
        <>
          {head("Cryptographic role", <BasisBadge basis={f.role.basis} />)}
          <p>{f.role.value ?? "Unknown — the scanner could not tell what this key is used for."}</p>
          {f.role.source ? <p className="small muted">Basis: {f.role.source}</p> : null}
          {f.role.basis !== "declared" ? <p className="note">Inferred roles come from identifier names. Confirm with the owning team before acting on them.</p> : null}
        </>
      );
    case "context":
      return (
        <>
          {head("Protocol / service context", <BasisBadge basis={f.context.basis} />)}
          <dl className="fields">
            <Field label="Context">{f.context.value ?? "Unknown"}</Field>
            <Field label="Service">{f.service ? `${f.service.name} (${f.service.kind})` : "Not mapped to a declared service"}</Field>
            <Field label="Source">{f.context.source ?? "—"}</Field>
          </dl>
        </>
      );
    case "dependencies":
      return (
        <>
          {head("Dependency connections", f.service ? <BasisBadge basis="declared" /> : <BasisBadge basis="unknown" />)}
          <dl className="fields">
            <Field label="Depends on">{f.dependencies.upstream.length ? f.dependencies.upstream.map((d) => <Badge key={d}>{d}</Badge>) : "None recorded"}</Field>
            <Field label="Depended on by">{f.dependencies.downstream.length ? f.dependencies.downstream.map((d) => <Badge key={d}>{d}</Badge>) : "None recorded"}</Field>
          </dl>
          <p className="small muted">Transitive, from declared and import-inferred edges. Runtime-only calls are not captured.</p>
          <Link className="btn btn-small" to="/anatomy/banking-dependencies">Open dependency anatomy</Link>
        </>
      );
    case "exposure":
      return (
        <>
          {head("Exposure and data lifetime", <BasisBadge basis={f.exposure.basis === "unknown" || f.dataLifetime.basis === "unknown" ? (f.exposure.basis === "unknown" && f.dataLifetime.basis === "unknown" ? "unknown" : "inferred") : "declared"} />)}
          <dl className="fields">
            <Field label="Exposure">{f.exposure.value ?? <em>Not declared</em>} <BasisBadge basis={f.exposure.basis} /></Field>
            <Field label="Data lifetime">{f.dataLifetime.value != null ? `${f.dataLifetime.value} years` : <em>Not declared</em>} <BasisBadge basis={f.dataLifetime.basis} /></Field>
          </dl>
        </>
      );
    case "risk":
      return (
        <>
          {head("Risk assessment", <RiskBadge risk={f.risk} />)}
          <table>
            <thead>
              <tr>
                <th>Factor</th>
                <th style={{ textAlign: "right" }}>Points</th>
              </tr>
            </thead>
            <tbody>
              {f.risk.factors.map((x, i) => (
                <tr key={i}>
                  <td>
                    {x.label} {x.basis === "missing" ? <Badge tone="amber">missing evidence</Badge> : null}
                  </td>
                  <td style={{ textAlign: "right" }} className="mono">+{x.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div>
            <strong className="small">Evidence that would improve this assessment</strong>
            <ul className="small">
              {f.missingEvidence.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          </div>
        </>
      );
    case "recommendation":
      return (
        <>
          {head("Migration recommendation", <Badge tone="amber">Rule-derived</Badge>)}
          <p>{f.recommendation.text}</p>
          <dl className="fields">
            <Field label="Target">{mono(f.recommendation.target)}</Field>
            <Field label="Standard">{f.recommendation.standard ?? "—"}</Field>
            {f.recommendation.blockedBy ? <Field label="Blocked by">{f.recommendation.blockedBy}</Field> : null}
          </dl>
        </>
      );
    case "verification":
      return (
        <>
          {head("Verification status", <VerdictBadge verdict={f.verification.status} />)}
          <p>{f.verification.label}</p>
          {f.patch ? (
            <>
              <p className="small mono">{f.patch.after.trim()}</p>
              <div className="kv">
                <Link className="btn btn-small btn-primary" to={`/verification?patch=${f.patch.id}`}>Open in Verification Center</Link>
                <Link className="btn btn-small" to={`/anatomy/verified-migration?patch=${f.patch.id}`}>Verification anatomy</Link>
              </div>
            </>
          ) : (
            <p className="note">{f.proposalBlocked ?? "No candidate patch exists."}</p>
          )}
        </>
      );
  }
}
