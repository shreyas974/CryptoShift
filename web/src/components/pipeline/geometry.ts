/**
 * Static geometry for the CryptoShift "sorting line" figure (anatomy kit, Figure size).
 *
 * The object: a bench conveyor. One crate per real service sits in its scheduled wave bay; crates pass an inventory
 * scanner gantry, a verification gate whose boom lifts only for a READY step, an approval stamp that only a human
 * lowers, and end at a rollback vault. World units: x along the line, y across it, z up. Pure: no DOM.
 */
import {
  corners,
  cylinder,
  depthOf,
  fitProjection,
  insetPlan,
  iso,
  lineOnTop,
  planOutline,
  radialTicks,
  ring,
  sideSeam,
  slabOf,
  topTicks,
  type Flat,
  type Plan,
  type Point3,
  type Projection,
  type SolidPaths,
} from "../iso/iso-kit";

export const WIDTH = 640;
export const HEIGHT = 340;
const AZ = 55; // shows the long side of the line

export const BASE: Plan = { x: 0, y: 0, w: 280, d: 96, r: 6 };
const BED: Plan = { x: 20, y: 26, w: 230, d: 36, r: 3 };
const BELT: Plan = { x: 22, y: 30, w: 226, d: 28, r: 2 };
const RAIL_BACK: Plan = { x: 20, y: 23, w: 230, d: 3, r: 1 };
const RAIL_FRONT: Plan = { x: 20, y: 62, w: 230, d: 3, r: 1 };
const LABEL: Plan = { x: 10, y: 72, w: 44, d: 16, r: 1.5 };
const RULER: Plan = { x: 64, y: 70, w: 170, d: 6, r: 1 };
const VAULT: Plan = { x: 252, y: 64, w: 24, d: 24, r: 2 };

export const P: Projection = fitProjection(
  [
    [0, 0, -4],
    [280, 0, -4],
    [0, 96, -4],
    [280, 96, -4],
    [36, 20, 60],
    [262, 12, 64],
    [240, 72, 62],
  ],
  WIDTH,
  HEIGHT,
  { pad: 26, azimuth: AZ },
);

export const at = (p: Point3): Flat => iso(p, P);
const depth = (x: number, y: number, z = 0) => depthOf([x, y, z], P);

export interface Part {
  key: string;
  paths: SolidPaths;
  tone: "hi" | "mid" | "lo" | "faint";
  halo?: boolean;
  inner?: string[];
  depth: number;
}

const part = (
  key: string,
  paths: SolidPaths,
  tone: Part["tone"],
  x: number,
  y: number,
  z = 0,
  extra: Partial<Part> = {},
): Part => ({
  key,
  paths,
  tone,
  depth: depth(x, y, z),
  ...extra,
});

// ---------------------------------------------------------------- base layer (feet, plate, groove, screws, label, ruler)
export const FEET: Part[] = corners(BASE, 14).map(([x, y], i) =>
  part(`foot${i}`, cylinder(x, y, 5, -4, 4, P, 28, 0.4), "lo", x, y),
);
export const BASE_PART = part("base", slabOf(BASE, 0, 8, P, 10, 1.2), "lo", 140, 48, 0, { halo: true });
export const GROOVE = planOutline(insetPlan(BASE, 4), 8, P, 10);
export const SCREWS: Flat[] = corners(BASE, 7).map(([x, y]) => at([x, y, 8]));
export const LABEL_PART = part("label", slabOf(LABEL, 8, 0.8, P, 6, 0.3), "mid", 32, 80, 8);
/** three engraved rule lines that stand for printed text (allowed to stop on the plate face) */
export const LABEL_RULES = [0, 1, 2].map((i) =>
  lineOnTop([LABEL.x + 5, LABEL.y + 4 + i * 4], [LABEL.x + (i === 2 ? 24 : 38), LABEL.y + 4 + i * 4], 8.8, P),
);
export const LABEL_SCREWS: Flat[] = corners(LABEL, 2).map(([x, y]) => at([x, y, 8.8]));
export const RULER_PART = part("ruler", slabOf(RULER, 8, 0.8, P, 4, 0.2), "mid", 149, 73, 8);
export const RULER_TICKS = topTicks(RULER.x + 2, RULER.x + RULER.w - 2, 5, 5, RULER.y, 8.8, [1.6, 3.2], P, "x");

// ---------------------------------------------------------------- conveyor
export const BED_PART = part("bed", slabOf(BED, 8, 6, P, 6, 0.8), "mid", 135, 44, 8);
export const BELT_PART = part("belt", slabOf(BELT, 14, 1.2, P, 6, 0.3), "lo", 135, 44, 14);
/** belt joints: run edge to edge across the belt top */
export const BELT_SEAMS = Array.from({ length: 18 }, (_, i) => BELT.x + 6 + i * 12.4).map((x) =>
  lineOnTop([x, BELT.y + 0.6], [x, BELT.y + BELT.d - 0.6], 15.2, P),
);
export const RAIL_BACK_PART = part("railB", slabOf(RAIL_BACK, 14, 4, P, 4, 0.4), "mid", 135, 24, 14);
export const RAIL_FRONT_PART = part("railF", slabOf(RAIL_FRONT, 14, 4, P, 4, 0.4), "mid", 135, 63, 14);
export const RAIL_SCREWS: Flat[] = Array.from({ length: 10 }, (_, i) => 26 + i * 24.5).flatMap((x) => [
  at([x, 24.5, 18]),
  at([x, 63.5, 18]),
]);

// ---------------------------------------------------------------- wave bays and crates (one crate per real service)
export const WAVE_X0 = 50;
export const WAVE_PITCH = 64;
export const CRATE = { w: 18, d: 20, h: 14, gap: 24, z: 15.2, y: 34 };

export function waveDividers(waves: number): { back: Part[]; front: Part[]; caps: Flat[] } {
  const xs = Array.from({ length: Math.max(0, waves - 1) }, (_, i) => WAVE_X0 + (i + 1) * WAVE_PITCH - 8);
  const post = (x: number, y: number, k: string) => part(k, cylinder(x, y, 1.6, 18, 12, P, 20, 0.2), "mid", x, y, 18);
  return {
    back: xs.map((x, i) => post(x, 24.5, `divB${i}`)),
    front: xs.map((x, i) => post(x, 63.5, `divF${i}`)),
    caps: xs.flatMap((x) => [at([x, 24.5, 30]), at([x, 63.5, 30])]),
  };
}

export interface CrateGeo {
  id: string;
  wave: number;
  body: Part;
  lid: string;
  lamp: SolidPaths;
  corners: Flat[];
  plate: string[];
}

/** crates are placed by scheduled wave and order within the wave (from the real plan) */
export function cratesOf(services: { id: string; wave: number }[]): CrateGeo[] {
  const perWave = new Map<number, number>();
  return services.map((s) => {
    const slot = perWave.get(s.wave) ?? 0;
    perWave.set(s.wave, slot + 1);
    const x = WAVE_X0 + s.wave * WAVE_PITCH + slot * CRATE.gap;
    const plan: Plan = { x, y: CRATE.y, w: CRATE.w, d: CRATE.d, r: 1.2 };
    const top = CRATE.z + CRATE.h;
    return {
      id: s.id,
      wave: s.wave,
      body: part(
        `crate-${s.id}`,
        slabOf(plan, CRATE.z, CRATE.h, P, 6, 0.6),
        "hi",
        x + CRATE.w / 2,
        CRATE.y + CRATE.d / 2,
        CRATE.z,
      ),
      lid: sideSeam(plan, CRATE.z + CRATE.h - 3, P, 6),
      lamp: cylinder(x + CRATE.w / 2, CRATE.y + CRATE.d / 2, 2.4, top, 1.4, P, 24, 0.3),
      corners: corners(plan, 2).map(([cx, cy]) => at([cx, cy, top])),
      plate: [lineOnTop([x + 3, CRATE.y + 3], [x + 9, CRATE.y + 3], top, P)],
    };
  });
}

// ---------------------------------------------------------------- inventory scanner gantry (first station)
export const SCAN = {
  postBack: part("scanPB", cylinder(36, 20, 2.4, 8, 46, P, 24, 0.3), "mid", 36, 20, 8),
  postFront: part("scanPF", cylinder(36, 68, 2.4, 8, 46, P, 24, 0.3), "mid", 36, 68, 8),
  bar: part("scanBar", slabOf({ x: 32.5, y: 17, w: 7, d: 54, r: 1 }, 54, 5, P, 4, 0.5), "mid", 36, 44, 54),
  head: part("scanHead", slabOf({ x: 31, y: 38, w: 10, d: 12, r: 1.5 }, 44, 10, P, 6, 0.5), "hi", 36, 44, 44),
  lens: ring(36, 44, 2.2, 44, P, 24),
  barScrews: [20, 44, 68].map((y) => at([36, y, 59])),
};

// ---------------------------------------------------------------- verification gate (boom lifts only for READY)
export const GATE = {
  post: part("gatePost", cylinder(239.5, 72.5, 3, 8, 34, P, 28, 0.4), "mid", 239.5, 72.5, 8),
  postCap: cylinder(239.5, 72.5, 3.6, 42, 2, P, 28, 0.3),
  boom: slabOf({ x: 237, y: 20, w: 5, d: 49, r: 1 }, 36, 3, P, 4, 0.4),
  boomStripes: [26, 34, 42, 50, 58].map((y) => lineOnTop([237.4, y], [241.6, y], 39, P)),
  lift: 16, // world units the boom rises when the step is READY
};

// ---------------------------------------------------------------- approval stamp (a human lowers it; plunger stays up)
export const STAMP = {
  column: part("stampCol", cylinder(264, 14, 3, 8, 54, P, 28, 0.4), "mid", 264, 14, 8),
  arm: part("stampArm", slabOf({ x: 261, y: 11, w: 6, d: 38, r: 1 }, 62, 4, P, 4, 0.4), "mid", 264, 30, 62),
  plunger: part("stampPl", cylinder(264, 44, 3, 44, 18, P, 28, 0.4), "hi", 264, 44, 44),
  knob: cylinder(264, 14, 4.2, 66, 3, P, 32, 0.3),
  pad: part("stampPad", slabOf({ x: 256, y: 36, w: 16, d: 16, r: 1.5 }, 8, 2, P, 6, 0.3), "lo", 264, 44, 8),
};

// ---------------------------------------------------------------- rollback vault (front right)
export const VAULT_GEO = {
  body: part("vault", slabOf(VAULT, 8, 22, P, 6, 0.8), "mid", 264, 76, 8),
  seam: sideSeam(VAULT, 18, P, 6),
  dialRing: ring(264, 76, 6, 30, P, 36),
  dialTicks: radialTicks(264, 76, 6, 24, 6, 30, [0.9, 1.8], P),
  knob: cylinder(264, 76, 2.6, 30, 2.4, P, 28, 0.3),
  screws: corners(VAULT, 2.5).map(([x, y]) => at([x, y, 30])),
};

export const HALO = BASE_PART.paths.fill;
export const byDepth = (a: { depth: number }, b: { depth: number }) => a.depth - b.depth;
export { WIDTH as FIG_W, HEIGHT as FIG_H };
