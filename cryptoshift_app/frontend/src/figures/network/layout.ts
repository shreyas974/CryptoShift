// Layout of the backplane bench from the backend's dependency graph and migration plan.
// Lane i holds migration wave i+1; a fenced holding bay at the end holds every blocked service.
import * as k from "../../anatomy/kit/iso-kit";
import type { Graph, Plan, GraphNode } from "../../api/types";

export const W = 760;
export const H = 470;
export const LANE = 62;
export const ROW = 46;
export const FOOT = { w: 32, d: 28 };

export interface Placed {
  node: GraphNode;
  lane: number;
  slot: number;
  cx: number;
  cy: number;
  top: number;
  status: "schedulable" | "blocked-cycle" | "blocked-upstream";
  wave: number | null;
  conflict: boolean;
}

export interface Layout {
  placed: Placed[];
  lanes: number;
  holding: boolean;
  waves: number;
  rows: number;
  bench: k.Plan;
  P: k.Projection;
  lift: Map<string, number>;
}

export const heightOf = (kind: string) =>
  ({ service: 18, api: 14, database: 19, pki: 16, "third-party": 16, config: 7, library: 10, client: 17 })[kind] ?? 14;

export function layoutOf(graph: Graph, plan: Plan): Layout {
  const byId = new Map(graph.nodes.map((n) => [n.id, n]));
  const conflicts = new Set(plan.compatibility.map((c) => c.node).filter(Boolean) as string[]);
  const placed: Placed[] = [];
  plan.waves.forEach((wave, lane) =>
    wave.forEach((id, slot) => {
      const node = byId.get(id)!;
      placed.push({ node, lane, slot, cx: 0, cy: 0, top: 0, status: "schedulable", wave: lane + 1, conflict: conflicts.has(id) });
    }),
  );
  const blocked = plan.steps.filter((s) => s.status !== "schedulable");
  const holdLane = plan.waves.length;
  // The holding bay is two columns wide so blocked services don't make one very tall lane.
  blocked.forEach((step, i) => {
    placed.push({ node: byId.get(step.node)!, lane: holdLane + (i % 2), slot: Math.floor(i / 2), cx: 0, cy: 0, top: 0, status: step.status, wave: null, conflict: conflicts.has(step.node) });
  });
  const lanes = holdLane + (blocked.length ? Math.min(2, blocked.length) : 0);
  const rows = Math.max(1, ...placed.map((p) => p.slot + 1));
  for (const p of placed) {
    const extra = p.lane >= holdLane ? 10 : 0;
    p.cx = 10 + LANE / 2 + p.lane * LANE + extra;
    p.cy = 14 + ROW / 2 + p.slot * ROW;
    p.top = 3 + 1.5 + heightOf(p.node.kind);
  }
  const bench: k.Plan = { x: 0, y: 0, w: 20 + lanes * LANE + (blocked.length ? 10 : 0), d: 28 + rows * ROW, r: 4 };
  const lift = new Map<string, number>();
  graph.edges.forEach((e, i) => lift.set(e.id, 9 + (i % 5) * 2.6));
  const pts: k.Point3[] = [
    [bench.x - 8, bench.y - 8, -6],
    [bench.x + bench.w + 8, bench.y - 8, -6],
    [bench.x - 8, bench.y + bench.d + 8, -6],
    [bench.x + bench.w + 8, bench.y + bench.d + 8, -6],
    [bench.x, bench.y, 60],
    [bench.x + bench.w, bench.y, 60],
    [bench.x, bench.y + bench.d, 40],
  ];
  const P = k.fitProjection(pts, W, H, { pad: 16, azimuth: 58 });
  return { placed, lanes, waves: plan.waves.length, holding: blocked.length > 0, rows, bench, P, lift };
}
