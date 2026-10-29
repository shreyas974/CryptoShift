// Reusable physical parts built on the Anatomy kit. Every builder returns server-safe JSX
// (no hooks), drawn back to front in the order the caller places it.
import * as React from "react";
import * as k from "./kit/iso-kit";
import { Solid, Line, Dots } from "./kit/react/draw";
import type { Plan, Projection, Plane, Point3, Tone } from "./kit/iso-kit";

export type P = Projection;

export const byDepth = <T extends { at: Plane; z?: number }>(items: T[], P: P) =>
  [...items].sort((a, b) => k.depthOf([a.at[0], a.at[1], a.z ?? 0], P) - k.depthOf([b.at[0], b.at[1], b.z ?? 0], P));

/** Four screw heads: a small ring with a dot, inset from the plan corners, on a top face. */
export function Screws({ P, plan, z, inset = 4, r = 1.1 }: { P: P; plan: Plan; z: number; inset?: number; r?: number }) {
  const pts = k.corners(plan, inset);
  return (
    <g>
      {pts.map(([x, y], i) => (
        <Line key={i} d={k.ring(x, y, r, z, P, 12)} tone="lo" />
      ))}
      <Dots points={pts.map(([x, y]) => k.iso([x, y, z], P))} size={0.45} tone="mid" />
    </g>
  );
}

/** A heavy base plate on round feet, with an inset groove and corner screws. */
export function BasePlate({ P, plan, z = 0, height = 8, feet = 4, tone = "mid" as Tone, groove = true }: { P: P; plan: Plan; z?: number; height?: number; feet?: number; tone?: Tone; groove?: boolean }) {
  const footAt = k.corners(plan, Math.min(14, plan.w / 5, plan.d / 4));
  const extra: Plane[] = feet > 4 ? [[plan.x + plan.w / 2, plan.y + Math.min(14, plan.d / 4)], [plan.x + plan.w / 2, plan.y + plan.d - Math.min(14, plan.d / 4)]] : [];
  const sorted = [...footAt, ...extra].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));
  return (
    <g>
      <path className="iso-halo" d={k.haloOf(plan, z - 6, height, P)} />
      {sorted.map(([x, y], i) => (
        <React.Fragment key={i}>
          <Solid paths={k.cylinder(x, y, 5, z - 6, 1.4, P, 24)} tone="lo" />
          <Solid paths={k.cylinder(x, y, 3.8, z - 4.6, 4.6, P, 24)} tone="mid" />
        </React.Fragment>
      ))}
      <Solid paths={k.slabOf(plan, z, height, P, 8, 1.4)} tone={tone} />
      {groove ? <Line d={k.planOutline(k.insetPlan(plan, 4.5), z + height, P)} tone="faint" /> : null}
      <Screws P={P} plan={plan} z={z + height} inset={8} r={1.6} />
    </g>
  );
}

/** A ruler strip flush on a top face, ticks rooted on its far edge. */
export function Ruler({ P, from, to, y, z, axis = "x", step = 4 }: { P: P; from: number; to: number; y: number; z: number; axis?: "x" | "y"; step?: number }) {
  const plan: Plan = axis === "x" ? { x: from, y, w: to - from, d: 6, r: 0.8 } : { x: y, y: from, w: 6, d: to - from, r: 0.8 };
  const t = k.topTicks(from + 2, to - 2, step, 5, y + 0.6, z + 0.5, [1.8, 3.2], P, axis);
  return (
    <g>
      <Solid paths={k.slabOf(plan, z, 0.5, P, 3)} tone="lo" crease="none" />
      <Line d={t.minor} tone="lo" />
      <Line d={t.major} tone="mid" />
    </g>
  );
}

/** A small engraved label plate with three printed rule lines and two screws. */
export function LabelPlate({ P, plan, z }: { P: P; plan: Plan; z: number }) {
  const top = z + 0.6;
  const x0 = plan.x + 2.4;
  const lines = [0.32, 0.55, 0.75].map((share, i) => {
    const y = plan.y + plan.d * share;
    const len = (plan.w - 7) * [0.85, 0.6, 0.4][i];
    return k.lineOnTop([x0, y], [x0 + len, y], top, P);
  });
  return (
    <g>
      <Solid paths={k.slabOf(plan, z, 0.6, P, 3)} tone="mid" />
      <Line d={k.planOutline(k.insetPlan(plan, 1), top, P)} tone="faint" />
      {lines.map((d, i) => (
        <Line key={i} d={d} tone="lo" free />
      ))}
      <Dots points={[k.iso([plan.x + plan.w - 2, plan.y + 1.6, top], P), k.iso([plan.x + plan.w - 2, plan.y + plan.d - 1.6, top], P)]} size={0.4} tone="mid" />
    </g>
  );
}

/** A status lamp: a bezel ring with a domed lens whose colour carries a verification state. */
export function Lamp({ P, at, z, status, r = 2.4 }: { P: P; at: Plane; z: number; status: string; r?: number }) {
  return (
    <g className="ax-lamp" data-status={status}>
      <Solid paths={k.cylinder(at[0], at[1], r + 0.9, z, 0.9, P, 24)} tone="lo" />
      <Solid paths={k.cylinder(at[0], at[1], r, z + 0.9, 1.1, P, 24)} tone="mid" className="ax-lens" />
    </g>
  );
}

/** A box module with a bevel, a seam band round its visible sides and corner screws on top. */
export function Module({ P, plan, z, height, tone = "hi", seams = [], screws = true, bevel = 1, children }: { P: P; plan: Plan; z: number; height: number; tone?: Tone; seams?: number[]; screws?: boolean; bevel?: number; children?: React.ReactNode }) {
  return (
    <g>
      <Solid
        paths={k.slabOf(plan, z, height, P, 6, bevel)}
        tone={tone}
        inner={seams.map((s, i) => (
          <Line key={i} d={k.sideSeam(plan, z + s, P, 6)} tone="faint" />
        ))}
      />
      {screws && plan.w > 12 && plan.d > 12 ? <Screws P={P} plan={plan} z={z + height} inset={3.2} r={0.9} /> : null}
      {children}
    </g>
  );
}

/** Vent slots: closed rounded slots on a top face, in a row along x. */
export function Vents({ P, x, y, z, count, gap = 3, length = 8 }: { P: P; x: number; y: number; z: number; count: number; gap?: number; length?: number }) {
  return (
    <g>
      {Array.from({ length: count }, (_, i) => (
        <Line key={i} d={k.planOutline({ x: x + i * gap, y, w: 1.2, d: length, r: 0.6 }, z, P, 4)} tone="lo" />
      ))}
    </g>
  );
}

/** A vertical post with a collar at its foot. */
export function Post({ P, at, z0, z1, r = 1.6, tone = "mid" as Tone }: { P: P; at: Plane; z0: number; z1: number; r?: number; tone?: Tone }) {
  return (
    <g>
      <Solid paths={k.cylinder(at[0], at[1], r + 1.2, z0, 1.6, P, 20)} tone="lo" />
      <Solid paths={k.cylinder(at[0], at[1], r, z0 + 1.6, z1 - z0 - 1.6, P, 20)} tone={tone} />
    </g>
  );
}

/** Screen anchor (viewBox coordinates) for a world point, used to pin HTML callouts. */
export const anchorOf = (point: Point3, P: P) => k.iso(point, P);

/** Wraps a selectable part so the frame can highlight it and route pointer events. */
export function Part({ id, state, children }: { id: string; state?: string; children: React.ReactNode }) {
  return (
    <g className="ax-part" data-part={id} data-state={state}>
      {children}
    </g>
  );
}
