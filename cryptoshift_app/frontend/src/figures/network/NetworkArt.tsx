// Fig 03: a backplane bench. Each service is a physical module whose form follows its kind; modules
// sit on mounting pads in lanes, one lane per migration wave. Overhead conduits are dependency edges.
import * as React from "react";
import * as k from "../../anatomy/kit/iso-kit";
import { Solid, Line, Dots, Wire } from "../../anatomy/kit/react/draw";
import { BasePlate, Lamp, Module, Part, Ruler, Screws, Vents, LabelPlate } from "../../anatomy/parts";
import { FOOT, LANE, heightOf, type Layout, type Placed } from "./layout";
import type { Graph } from "../../api/types";

const PAD_Z = 3;

function ModuleBody({ p, P }: { p: Placed; P: k.Projection }) {
  const { cx, cy } = p;
  const z = PAD_Z + 1.5;
  const h = heightOf(p.node.kind);
  const plan: k.Plan = { x: cx - FOOT.w / 2, y: cy - FOOT.d / 2, w: FOOT.w, d: FOOT.d, r: 1.6 };
  const top = z + h;
  const lampAt: k.Plane = [cx + FOOT.w / 2 - 5, cy + FOOT.d / 2 - 5];
  const lamp = p.status !== "schedulable" ? "failed" : p.conflict ? "pending" : "unrun";
  switch (p.node.kind) {
    case "database": {
      const discs = [0, 1, 2];
      return (
        <g>
          {discs.map((i) => (
            <Solid key={i} paths={k.cylinder(cx, cy, 12.5, z + i * 6.3, 6, P, 40, 0.6)} tone="hi" inner={<Line d={k.sideArc(cx, cy, 12.5, z + i * 6.3 + 3, P)} tone="faint" />} />
          ))}
          <Line d={k.ring(cx, cy, 8, z + 18.9, P, 32)} tone="faint" />
          <Lamp P={P} at={[cx, cy]} z={z + 18.9} status={lamp} r={2} />
        </g>
      );
    }
    case "config": {
      const sw = Array.from({ length: 6 }, (_, i) => i);
      return (
        <g>
          <Module P={P} plan={plan} z={z} height={h} tone="hi" seams={[2.5]} />
          {/* a bank of DIP switches: each toggle is one TLS policy setting */}
          <Solid paths={k.slabOf({ x: cx - 12, y: cy - 6, w: 24, d: 9, r: 0.8 }, top, 1.6, P, 2)} tone="mid" />
          {sw.map((i) => (
            <Solid key={i} paths={k.slabOf({ x: cx - 10.5 + i * 3.8, y: cy - 4.6 + (i % 2 ? 0 : 2.6), w: 2, d: 3.4, r: 0.3 }, top + 1.6, 1.6, P, 2)} tone="hi" />
          ))}
          <Lamp P={P} at={lampAt} z={top} status={lamp} r={1.8} />
        </g>
      );
    }
    case "library":
      return (
        <g>
          <Module P={P} plan={plan} z={z} height={h} tone="hi" seams={[3, 7]} />
          {[-8, -4, 0, 4, 8].map((dx) => (
            <Line key={dx} d={k.lineOnTop([cx + dx, plan.y + 3], [cx + dx, plan.y + plan.d - 3], top, P)} tone="lo" />
          ))}
          <Line d={k.planOutline(k.insetPlan(plan, 2.4), top, P)} tone="faint" />
          <Lamp P={P} at={lampAt} z={top} status={lamp} r={1.8} />
        </g>
      );
    case "client":
      return (
        <g>
          <Module P={P} plan={{ ...plan, d: plan.d - 6, y: plan.y + 6 }} z={z} height={4} tone="mid" screws={false} />
          {/* a terminal: upright screen housing with an inset screen */}
          <Solid paths={k.slabOf({ x: cx - 13, y: cy - 4, w: 26, d: 5, r: 0.8 }, z + 4, h - 4, P, 2, 0.6)} tone="hi" />
          <Line d={k.pathOf([k.iso([cx - 11, cy + 1.05, z + 6.5], P), k.iso([cx + 11, cy + 1.05, z + 6.5], P), k.iso([cx + 11, cy + 1.05, z + h - 2], P), k.iso([cx - 11, cy + 1.05, z + h - 2], P)], true)} tone="mid" />
          <Dots points={[k.iso([cx + 9, cy + 1.1, z + 5.2], P)]} size={0.5} tone="hi" />
          <Lamp P={P} at={[cx + 10, cy + 9]} z={z + 4} status={lamp} r={1.8} />
        </g>
      );
    case "pki":
      return (
        <g>
          <Module P={P} plan={plan} z={z} height={h} tone="hi" seams={[4, h - 3]} />
          {/* a vault dial and a key slot: the issuing CA's key ceremony */}
          <Solid paths={k.cylinder(cx - 4, cy - 2, 6.5, top, 2.4, P, 32, 0.4)} tone="mid" />
          <Line d={k.radialTicks(cx - 4, cy - 2, 6, 12, 3, top + 2.4, [0.8, 1.6], P).major} tone="lo" />
          <Line d={k.planOutline({ x: cx + 5, y: cy - 6, w: 2, d: 8, r: 0.6 }, top, P, 3)} tone="mid" />
          <Lamp P={P} at={lampAt} z={top} status={lamp} r={1.8} />
        </g>
      );
    case "third-party":
      return (
        <g>
          <Module P={P} plan={plan} z={z} height={h} tone="mid" seams={[4, h - 3]} />
          {/* a sealed vendor plate: the code inside is not ours to patch */}
          <LabelPlate P={P} plan={{ x: cx - 11, y: cy - 8, w: 16, d: 12, r: 0.8 }} z={top} />
          <Solid paths={k.cylinder(cx + 8, cy - 3, 2.6, top, 1, P, 20)} tone="lo" />
          <Lamp P={P} at={lampAt} z={top} status={lamp} r={1.8} />
        </g>
      );
    case "api":
      return (
        <g>
          <Module P={P} plan={plan} z={z} height={h} tone="hi" seams={[4]} />
          {/* a row of port sockets: routes the gateway exposes */}
          {[-10, -4, 2, 8].map((dx) => (
            <React.Fragment key={dx}>
              <Solid paths={k.cylinder(cx + dx, cy - 5, 2, top, 1.4, P, 16)} tone="mid" />
              <Line d={k.ring(cx + dx, cy - 5, 0.9, top + 1.4, P, 12)} tone="lo" />
            </React.Fragment>
          ))}
          <Lamp P={P} at={lampAt} z={top} status={lamp} r={1.8} />
        </g>
      );
    default:
      return (
        <g>
          <Module P={P} plan={plan} z={z} height={h} tone="hi" seams={[4, h - 4]} />
          <Vents P={P} x={plan.x + 4} y={cy - 6} z={top} count={5} gap={3.2} length={9} />
          <Lamp P={P} at={lampAt} z={top} status={lamp} r={1.8} />
        </g>
      );
  }
}

export const portOf = (p: Placed): k.Point3 => [p.cx - 6, p.cy + 7, PAD_Z + 1.5 + heightOf(p.node.kind)];

export function Bench({ layout }: { layout: Layout }) {
  const { bench, P, waves, holding } = layout;
  const holdX = bench.x + 10 + waves * LANE + 4;
  return (
    <g key="bench">
      <BasePlate P={P} plan={bench} z={-6} height={6} feet={6} />
      <Ruler P={P} from={bench.x + 8} to={bench.x + bench.w - 8} y={bench.y + bench.d - 9} z={0} />
      {/* lane rails between migration waves */}
      {Array.from({ length: waves + 1 }, (_, i) => (
        <Solid key={i} paths={k.slabOf({ x: bench.x + 9 + i * LANE, y: bench.y + 8, w: 2, d: bench.d - 20, r: 0.6 }, 0, 1.6, P, 2)} tone="lo" />
      ))}
      {holding ? (
        <g>
          {/* the holding bay: a fenced area for services that cannot be scheduled */}
          <Solid paths={k.slabOf({ x: holdX + 2, y: bench.y + 6, w: bench.x + bench.w - holdX - 8, d: bench.d - 18, r: 2 }, 0, 0.8, P, 4)} tone="lo" crease="none" />
          <Line d={k.planOutline({ x: holdX + 5, y: bench.y + 9, w: bench.x + bench.w - holdX - 14, d: bench.d - 24, r: 1 }, 0.8, P)} tone="red" dashed />
        </g>
      ) : null}
    </g>
  );
}

export function Pads({ layout }: { layout: Layout }) {
  const { P } = layout;
  const sorted = [...layout.placed].sort((a, b) => k.depthOf([a.cx, a.cy, 0], P) - k.depthOf([b.cx, b.cy, 0], P));
  return (
    <g key="pads">
      {sorted.map((p) => {
        const pad: k.Plan = { x: p.cx - FOOT.w / 2 - 3, y: p.cy - FOOT.d / 2 - 3, w: FOOT.w + 6, d: FOOT.d + 6, r: 1.5 };
        return (
          <g key={p.node.id}>
            <Solid paths={k.slabOf(pad, 0, PAD_Z, P, 4, 0.6)} tone="lo" />
            <Screws P={P} plan={pad} z={PAD_Z} inset={2} r={0.7} />
          </g>
        );
      })}
    </g>
  );
}

export function Modules({ layout }: { layout: Layout }) {
  const { P } = layout;
  const sorted = [...layout.placed].sort((a, b) => k.depthOf([a.cx, a.cy, 0], P) - k.depthOf([b.cx, b.cy, 0], P));
  return (
    <g key="modules">
      {sorted.map((p) => (
        <Part key={p.node.id} id={p.node.id} state={p.status}>
          <ModuleBody p={p} P={P} />
        </Part>
      ))}
    </g>
  );
}

export function Conduits({ layout, graph, cycleEdges, hl }: { layout: Layout; graph: Graph; cycleEdges: Set<string>; hl: Map<string, "up" | "down"> }) {
  const { P } = layout;
  const at = new Map(layout.placed.map((p) => [p.node.id, p]));
  return (
    <g key="conduits">
      {graph.edges.map((e) => {
        const a = at.get(e.from);
        const b = at.get(e.to);
        if (!a || !b) return null;
        const pa = portOf(a);
        const pb = portOf(b);
        const lift = layout.lift.get(e.id) ?? 30;
        const z = Math.max(pa[2], pb[2]) + lift;
        return (
          <g key={e.id} className="ax-edge" data-basis={e.basis} data-cycle={cycleEdges.has(e.id) ? "" : undefined} data-hl={hl.get(e.id)}>
            <Wire from={k.iso(pa, P)} via={[k.iso([pa[0], pa[1], z], P), k.iso([pb[0], pb[1], z], P)]} to={k.iso(pb, P)} tone="mid" size={1.4} />
          </g>
        );
      })}
    </g>
  );
}

export function NetworkPreview({ layout, graph, cycleEdges }: { layout: Layout; graph: Graph; cycleEdges: Set<string> }) {
  return (
    <g>
      <Bench layout={layout} />
      <Pads layout={layout} />
      <Modules layout={layout} />
      <Conduits layout={layout} graph={graph} cycleEdges={cycleEdges} hl={new Map()} />
    </g>
  );
}
