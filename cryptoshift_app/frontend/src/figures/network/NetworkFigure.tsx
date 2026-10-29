import * as React from "react";
import { Link } from "react-router-dom";
import * as k from "../../anatomy/kit/iso-kit";
import { AnatomyFrame, type PartInfo, type PartStatus } from "../../anatomy/AnatomyFrame";
import { Bench, Pads, Modules, Conduits } from "./NetworkArt";
import { layoutOf, W, H, heightOf } from "./layout";
import type { Graph, Plan, GraphEdge } from "../../api/types";
import { Badge, Field } from "../../components/ui";

const KIND: Record<string, string> = {
  service: "Service",
  api: "Internal API",
  database: "Database",
  pki: "Certificate infrastructure",
  "third-party": "Third-party library",
  config: "TLS / configuration layer",
  library: "Shared library",
  client: "Dependent client service",
};

export function useNetwork(graph: Graph, plan: Plan) {
  return React.useMemo(() => {
    const layout = layoutOf(graph, plan);
    const cycleEdges = new Set(plan.cycles.flatMap((c) => c.edges.map((e) => e.id)));
    return { layout, cycleEdges };
  }, [graph, plan]);
}

export function NetworkFigure({ graph, plan, toolbar }: { graph: Graph; plan: Plan; toolbar?: React.ReactNode }) {
  const { layout, cycleEdges } = useNetwork(graph, plan);
  const [selected, setSelected] = React.useState<string | null>(plan.cycles[0]?.members[0] ?? null);
  const visibleEdges = plan.includeInferred ? graph.edges : graph.edges.filter((e) => e.basis === "known");
  const shownGraph = { ...graph, edges: visibleEdges };
  const node = (id: string) => graph.nodes.find((n) => n.id === id)!;
  const stepOf = (id: string) => plan.steps.find((s) => s.node === id)!;
  const sel = selected ? node(selected) : null;

  // Upstream = what must migrate first; downstream = what is affected by this change.
  const hl = new Map<string, "up" | "down">();
  if (sel) {
    const up = new Set([sel.id, ...sel.dependencies]);
    const down = new Set([sel.id, ...sel.dependents]);
    for (const e of visibleEdges) {
      if (up.has(e.from) && sel.dependencies.includes(e.to)) hl.set(e.id, "up");
      else if (down.has(e.to) && sel.dependents.includes(e.from)) hl.set(e.id, "down");
    }
  }

  const parts: PartInfo[] = layout.placed.map((p) => {
    const step = stepOf(p.node.id);
    const status: PartStatus = step.status !== "schedulable" ? "blocked" : p.conflict ? "pending" : "neutral";
    return {
      id: p.node.id,
      label: p.node.name,
      summary:
        step.status === "schedulable"
          ? `Wave ${step.wave}. ${step.prerequisites.length ? `After ${step.prerequisites.join(", ")}.` : "No prerequisites."}${p.conflict ? " Has a failed candidate patch." : ""}`
          : step.status === "blocked-cycle"
            ? `Blocked: dependency cycle with ${step.blockedBy.join(", ")}.`
            : `Blocked until ${step.blockedBy.join(", ")} can be scheduled.`,
      readout: step.wave ? `${p.node.id} · wave ${step.wave}` : `${p.node.id} · blocked`,
      status,
      statusLabel: step.status === "schedulable" ? (p.conflict ? "Compatibility conflict" : `Wave ${step.wave}`) : "Blocked",
      anchor: k.iso([p.cx, p.cy, 3 + 1.5 + heightOf(p.node.kind)], layout.P),
      related: [...p.node.dependencies, ...p.node.dependents],
    };
  });

  return (
    <>
      <AnatomyFrame
        fig="Fig 03"
        title="Banking dependencies"
        ariaLabel="Backplane bench of NorthBank services arranged by migration wave, with dependency conduits"
        width={W}
        height={H}
        parts={parts}
        selected={selected}
        onSelect={setSelected}
        idleReadout={plan.valid ? `${plan.waves.length} waves · valid order` : `${plan.cycles.length} cycle · order blocked`}
        hint="Select a module"
        keys={[
          { mark: "raised", label: "Service module (lane = migration wave)" },
          { mark: "dim", label: "Declared dependency" },
          { mark: "dashed", label: "Import-inferred dependency" },
          { mark: "red", label: "Cycle / holding bay" },
        ]}
        caption={
          <span>
            Lanes run left to right in the backend's migration order: a service only enters a lane once everything it depends on sits in an earlier lane. Orange conduits are what the selected service waits on; blue conduits are what it affects. {graph.note}
          </span>
        }
        toolbar={toolbar}
        detail={sel ? <NodeDetail id={sel.id} graph={graph} plan={plan} /> : <p className="muted">Select a module to see its prerequisites and the services its migration affects.</p>}
      >
        <Bench layout={layout} />
        <Pads layout={layout} />
        <Modules layout={layout} />
        <Conduits layout={layout} graph={shownGraph} cycleEdges={cycleEdges} hl={hl} />
      </AnatomyFrame>
      <FlatGraph graph={shownGraph} plan={plan} selected={selected} onSelect={setSelected} cycleEdges={cycleEdges} hl={hl} />
    </>
  );
}

function NodeDetail({ id, graph, plan }: { id: string; graph: Graph; plan: Plan }) {
  const n = graph.nodes.find((x) => x.id === id)!;
  const step = plan.steps.find((s) => s.node === id)!;
  const edgesOut = graph.edges.filter((e) => e.from === id && (plan.includeInferred || e.basis === "known"));
  const conflicts = plan.compatibility.filter((c) => c.node === id);
  const cycle = plan.cycles.find((c) => c.members.includes(id));
  return (
    <>
      <div className="kv" style={{ justifyContent: "space-between" }}>
        <h3>{n.name}</h3>
        {step.status === "schedulable" ? <Badge tone="blue">Wave {step.wave}</Badge> : <Badge tone="red">{step.status === "blocked-cycle" ? "Cycle" : "Blocked"}</Badge>}
      </div>
      <dl className="fields">
        <Field label="Kind">{KIND[n.kind] ?? n.kind}</Field>
        <Field label="Path"><code className="mono">{n.path}</code></Field>
        <Field label="Exposure">{n.exposure ?? "Not declared"}</Field>
        <Field label="Findings">{n.findings ? `${n.findings} (max risk ${n.maxRisk})` : "None"}</Field>
        <Field label="Affected chain">{n.dependents.length ? n.dependents.join(" → ") : "No dependents"}</Field>
      </dl>
      <div>
        <strong className="small">Migration prerequisites</strong>
        {edgesOut.length ? (
          <ul className="list small" style={{ marginTop: 6 }}>
            {edgesOut.map((e) => (
              <EdgeItem key={e.id} e={e} />
            ))}
          </ul>
        ) : (
          <p className="small muted">None: can be migrated first.</p>
        )}
      </div>
      {cycle ? (
        <div className="banner banner-error small" style={{ margin: 0 }}>
          Dependency cycle: {cycle.members.join(" ↔ ")}. No valid order exists until one of these edges is removed or confirmed false:
          <ul>
            {cycle.edges.map((e) => (
              <li key={e.id}>
                {e.from} → {e.to} ({e.basis}
                {e.evidence[0]?.file ? `, ${e.evidence[0].file}:${e.evidence[0].line}` : ""})
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {step.status === "blocked-upstream" ? <p className="note">Waiting on: {step.blockedBy.join(", ")}.</p> : null}
      {conflicts.map((c) => (
        <div key={c.patchId} className="banner banner-warn small" style={{ margin: 0 }}>
          Compatibility conflict: {c.check} failed for <code>{c.file}:{c.line}</code> — {c.detail}{" "}
          <Link to={`/verification?patch=${c.patchId}`}>View run</Link>
        </div>
      ))}
    </>
  );
}

function EdgeItem({ e }: { e: GraphEdge }) {
  return (
    <li>
      <Badge tone={e.basis === "known" ? "green" : "amber"}>{e.basis === "known" ? "Declared" : "Inferred"}</Badge>
      <span>
        {e.to}
        {e.basis === "inferred" && e.evidence[0]?.file ? (
          <span className="muted">
            {" "}
            · <code>{e.evidence[0].file}:{e.evidence[0].line}</code>
          </span>
        ) : null}
        {e.confirmedByImport ? <span className="muted"> · confirmed by import</span> : null}
      </span>
    </li>
  );
}

/** A plain, readable layered graph synchronised with the figure's selection. */
function FlatGraph({ graph, plan, selected, onSelect, cycleEdges, hl }: { graph: Graph; plan: Plan; selected: string | null; onSelect: (id: string) => void; cycleEdges: Set<string>; hl: Map<string, "up" | "down"> }) {
  const columns: { title: string; ids: string[] }[] = plan.waves.map((w, i) => ({ title: `Wave ${i + 1}`, ids: w }));
  const blocked = plan.steps.filter((s) => s.status !== "schedulable").map((s) => s.node);
  if (blocked.length) columns.push({ title: "Blocked", ids: blocked });
  const colW = 150;
  const rowH = 46;
  const width = columns.length * colW + 20;
  const height = Math.max(...columns.map((c) => c.ids.length)) * rowH + 50;
  const pos = new Map<string, [number, number]>();
  columns.forEach((c, i) => c.ids.forEach((id, j) => pos.set(id, [14 + i * colW, 40 + j * rowH])));
  const nodeW = 128;
  return (
    <section className="card" style={{ marginTop: 16 }} aria-label="Dependency graph">
      <div className="card-head">
        <h2>Dependency graph</h2>
        <span className="small muted">Same data and selection as the figure · arrows point from a service to what it depends on</span>
      </div>
      <div style={{ overflowX: "auto" }}>
        <svg className="flat-graph" viewBox={`0 0 ${width} ${height}`} width={width} height={height} style={{ maxWidth: "none" }} role="img" aria-label="Layered dependency graph">
          <defs>
            <marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0 0 8 4 0 8z" fill="context-stroke" />
            </marker>
          </defs>
          {columns.map((c, i) => (
            <text key={c.title} x={14 + i * colW} y={20} className="fg-col">
              {c.title}
            </text>
          ))}
          {graph.edges.map((e) => {
            const a = pos.get(e.from);
            const b = pos.get(e.to);
            if (!a || !b) return null;
            const x1 = a[0];
            const y1 = a[1] + 14;
            const x2 = b[0] + nodeW;
            const y2 = b[1] + 14;
            const back = x2 > x1;
            const d = back ? `M${x1 + nodeW / 2} ${y1 + 14} C${x1 + nodeW / 2} ${y1 + 44} ${x2 - nodeW / 2} ${y2 + 44} ${x2 - nodeW / 2} ${y2 + 15}` : `M${x1} ${y1} C${x1 - 30} ${y1} ${x2 + 30} ${y2} ${x2 + 1} ${y2}`;
            return <path key={e.id} d={d} className="fg-edge" data-basis={e.basis} data-cycle={cycleEdges.has(e.id) ? "" : undefined} data-hl={hl.get(e.id)} markerEnd="url(#arrow)" />;
          })}
          {[...pos.entries()].map(([id, [x, y]]) => {
            const n = graph.nodes.find((g) => g.id === id)!;
            const isSel = id === selected;
            return (
              <g key={id} className="fg-node" data-selected={isSel ? "" : undefined} data-blocked={blocked.includes(id) ? "" : undefined} tabIndex={0} role="button" aria-pressed={isSel} aria-label={n.name} onClick={() => onSelect(id)} onKeyDown={(ev) => (ev.key === "Enter" || ev.key === " ") && (ev.preventDefault(), onSelect(id))}>
                <rect x={x} y={y} width={nodeW} height={28} rx={6} />
                <text x={x + 10} y={y + 18}>
                  {n.name.length > 19 ? n.name.slice(0, 18) + "…" : n.name}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </section>
  );
}
