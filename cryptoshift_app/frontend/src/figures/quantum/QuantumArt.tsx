// Fig 01: a superconducting quantum computer in a dilution refrigerator, drawn as a cutaway
// (shields removed). Plates shrink as the stages get colder; control lines carry attenuators down
// through every stage; the readout line climbs back through an isolator and a 4 K amplifier.
import * as React from "react";
import * as k from "../../anatomy/kit/iso-kit";
import { Solid, Line, Dots, Wire } from "../../anatomy/kit/react/draw";
import { BasePlate, Part, Post, Screws, Lamp, Vents } from "../../anatomy/parts";
import type { QId } from "./model";

export const W = 700;
export const H = 640;

const FLOOR = 8;
const BASE: k.Plan = { x: -64, y: -64, w: 252, d: 128, r: 4 };
const TOPBAR = 262;
const POSTS: k.Plane[] = [
  [-52, -52],
  [52, -52],
  [-52, 52],
  [52, 52],
];

interface Stage {
  r: number;
  z: number;
  h: number;
}
// top flange, 50 K, 4 K, still, cold plate, mixing chamber
export const STAGE_GEO: Stage[] = [
  { r: 44, z: 242, h: 8 },
  { r: 40, z: 206, h: 4 },
  { r: 35, z: 172, h: 4 },
  { r: 30, z: 140, h: 4 },
  { r: 26, z: 110, h: 3.5 },
  { r: 22, z: 80, h: 5 },
];
const top = (s: Stage) => s.z + s.h;

const polar = (deg: number, r: number): k.Plane => [r * Math.cos((deg * Math.PI) / 180), r * Math.sin((deg * Math.PI) / 180)];
const CONTROL: k.Plane[] = [polar(78, 16.5), polar(58, 16.5)];
const READOUT: k.Plane = polar(16, 16.5);
const ROD_ANGLES = [100, 220, 340];

export const P = k.fitProjection(
  [
    [BASE.x, BASE.y, -6],
    [BASE.x + BASE.w, BASE.y, -6],
    [BASE.x, BASE.y + BASE.d, -6],
    [BASE.x + BASE.w, BASE.y + BASE.d, -6],
    [-56, -56, 284],
    [56, 56, 284],
    [170, -40, 284],
  ],
  W,
  H,
  { pad: 12, azimuth: 33 },
);

const depth = (pt: k.Plane, z = 0) => k.depthOf([pt[0], pt[1], z], P);

export function anchorOf(id: QId): [number, number] {
  const at: Record<QId, k.Point3> = {
    cryostat: [-30, 30, 190],
    io: [CONTROL[0][0], CONTROL[0][1], 256],
    control: [CONTROL[0][0], CONTROL[0][1], 190],
    attenuators: [CONTROL[1][0], CONTROL[1][1], top(STAGE_GEO[3]) + 4],
    readout: [READOUT[0], READOUT[1], 155],
    package: [0, 13, 47],
    chip: [6.5, 6.5, 51],
    "control-electronics": [168, -30, 90],
    "readout-electronics": [168, 19, 38],
    computer: [150, 22, 70],
    shielding: [100, 44, 50],
  };
  return k.iso(at[id], P);
}

function Frame({ front }: { front: boolean }) {
  const posts = POSTS.filter((p) => (depth(p) > 1) === front);
  return (
    <g>
      {posts.map((p, i) => (
        <Post key={i} P={P} at={p} z0={FLOOR} z1={TOPBAR} r={2.4} tone="mid" />
      ))}
    </g>
  );
}

function TopFrame() {
  const bars: k.Plan[] = [
    { x: -56, y: -56, w: 112, d: 6, r: 1 },
    { x: -56, y: -56, w: 6, d: 112, r: 1 },
    { x: -3, y: -56, w: 6, d: 112, r: 1 },
    { x: -56, y: -3, w: 112, d: 6, r: 1 },
    { x: 50, y: -56, w: 6, d: 112, r: 1 },
    { x: -56, y: 50, w: 112, d: 6, r: 1 },
  ];
  const hangers: k.Plane[] = [
    [-36, 0],
    [0, -36],
    [36, 0],
    [0, 36],
  ].sort((a, b) => depth(a as k.Plane) - depth(b as k.Plane)) as k.Plane[];
  return (
    <g>
      {hangers.map((h, i) => (
        <Solid key={i} paths={k.cylinder(h[0], h[1], 1.6, top(STAGE_GEO[0]), TOPBAR - top(STAGE_GEO[0]), P, 16)} tone="mid" />
      ))}
      {bars.map((b, i) => (
        <Solid key={i} paths={k.slabOf(b, TOPBAR, 4, P, 2, 0.5)} tone="mid" />
      ))}
      <Dots points={POSTS.map(([x, y]) => k.iso([x + Math.sign(x) * 1, y + Math.sign(y) * 1, TOPBAR + 4], P))} size={0.6} tone="mid" />
    </g>
  );
}

function Plate({ s, tone = "hi" as k.Tone, lit = false }: { s: Stage; tone?: k.Tone; lit?: boolean }) {
  return (
    <g>
      <Solid paths={k.cylinder(0, 0, s.r, s.z, s.h, P, 64, 0.8)} tone={tone} lit={lit} inner={s.h > 4.5 ? <Line d={k.sideArc(0, 0, s.r, s.z + s.h / 2, P, 32)} tone="faint" /> : null} />
      <Line d={k.ring(0, 0, s.r - 3.5, top(s), P, 48)} tone="faint" />
    </g>
  );
}

/** Things that stand between two plates, painted back to front: rods, line segments, attenuators. */
function Level({ lower, upper, index }: { lower: Stage; upper: Stage; index: number }) {
  type Item = { at: k.Plane; node: React.ReactNode; part: QId };
  const items: Item[] = [];
  const z0 = top(lower);
  const z1 = upper.z;
  for (const a of ROD_ANGLES) {
    const at = polar(a + index * 9, lower.r - 4);
    items.push({ at, part: "cryostat", node: <Solid paths={k.cylinder(at[0], at[1], 1.3, z0, z1 - z0, P, 14)} tone="mid" crease="none" /> });
  }
  const attH = 6;
  CONTROL.forEach((at, i) => {
    items.push({
      at,
      part: "control",
      node: (
        <g>
          <Line d={k.segment([at[0], at[1], z0 + attH], [at[0], at[1], z1], P)} tone="hi" />
          <Line d={k.segment([at[0], at[1], z0 + attH], [at[0], at[1], z1], P)} tone="lit" className="ax-pulse ax-flow" />
        </g>
      ),
    });
    items.push({
      at: [at[0] + 0.01 * i, at[1]],
      part: "attenuators",
      node: (
        <g>
          <Solid paths={k.cylinder(at[0], at[1], 2.4, z0, attH, P, 18, 0.3)} tone="hi" inner={<Line d={k.sideArc(at[0], at[1], 2.4, z0 + 3, P, 12)} tone="lo" />} />
        </g>
      ),
    });
  });
  // readout: isolator on the mixing chamber, HEMT amplifier on the 4 K plate
  const readoutBox = index === 0 ? { w: 7, d: 5, h: 5 } : index === 3 ? { w: 9, d: 7, h: 6 } : null;
  const rz = readoutBox ? z0 + readoutBox.h : z0;
  items.push({
    at: READOUT,
    part: "readout",
    node: (
      <g>
        {readoutBox ? (
          <Solid paths={k.slabOf({ x: READOUT[0] - readoutBox.w / 2, y: READOUT[1] - readoutBox.d / 2, w: readoutBox.w, d: readoutBox.d, r: 0.6 }, z0, readoutBox.h, P, 2, 0.4)} tone="hi" />
        ) : null}
        <Line d={k.segment([READOUT[0], READOUT[1], rz], [READOUT[0], READOUT[1], z1], P)} tone="hi" />
        <Line d={k.segment([READOUT[0], READOUT[1], rz], [READOUT[0], READOUT[1], z1], P)} tone="lit" className="ax-pulse ax-flow-up" />
      </g>
    ),
  });
  // still pot above the still plate; mixing-chamber pot above the mixing-chamber plate
  if (index === 2 || index === 0) {
    const r = index === 2 ? 9 : 7.5;
    const at: k.Plane = [-6, -8];
    items.push({ at, part: "cryostat", node: <Solid paths={k.cylinder(at[0], at[1], r, z0, Math.min(12, z1 - z0 - 6), P, 36, 0.6)} tone="hi" inner={<Line d={k.sideArc(at[0], at[1], r, z0 + 4, P)} tone="faint" />} /> });
  }
  items.sort((a, b) => depth(a.at) - depth(b.at));
  return (
    <g>
      {items.map((it, i) => (
        <Part key={i} id={it.part}>
          {it.node}
        </Part>
      ))}
    </g>
  );
}

function Package() {
  const pkg: k.Plan = { x: -13, y: -13, w: 26, d: 26, r: 2 };
  const mxc = STAGE_GEO[5];
  return (
    <g>
      <Part id="package">
        <Solid paths={k.cylinder(0, 0, 3.4, 50, mxc.z - 50, P, 20)} tone="mid" />
        <Solid paths={k.slabOf(pkg, 44, 6, P, 4, 0.6)} tone="hi" inner={<Line d={k.sideSeam(pkg, 46.5, P, 4)} tone="faint" />} />
        <Screws P={P} plan={pkg} z={50} inset={2.6} r={0.8} />
      </Part>
      {/* lines drop from the mixing chamber to SMA connectors on the package rim */}
      {[...CONTROL.map((c) => ({ c, part: "control" as QId })), { c: READOUT, part: "readout" as QId }].map(({ c, part }, i) => {
        const end: k.Point3 = [Math.max(-11, Math.min(11, c[0])), Math.max(-11, Math.min(11, c[1])), 50];
        return (
          <Part key={i} id={part}>
            <Solid paths={k.cylinder(end[0], end[1], 1.5, 50, 2, P, 14)} tone="mid" />
            <Wire from={k.iso([c[0], c[1], mxc.z], P)} via={[k.iso([c[0], c[1], 60], P)]} to={k.iso([end[0], end[1], 52], P)} tone="hi" size={0.8} />
          </Part>
        );
      })}
      <Part id="chip">
        <Solid paths={k.slabOf({ x: 2, y: 2, w: 9, d: 9, r: 0.4 }, 50, 0.9, P, 2)} tone="hi" lit />
        <Dots points={k.dotGrid(3.8, 3.8, 4, 4, 1.8, 50.9, P)} size={0.35} tone="hi" pulse />
        <Dots points={[0, 2, 4, 6, 8].map((d) => k.iso([1.2, 2.5 + d, 50.2], P))} size={0.3} tone="mid" />
      </Part>
    </g>
  );
}

function ShieldCan() {
  const [cx, cy] = [100, 44];
  return (
    <Part id="shielding">
      <Solid paths={k.cylinder(cx, cy, 23, FLOOR, 3, P, 56, 0.6)} tone="lo" halo />
      <Solid paths={k.cylinder(cx, cy, 20, FLOOR + 3, 52, P, 56, 0.8)} tone="hi" inner={<>{[16, 34].map((z) => <Line key={z} d={k.sideArc(cx, cy, 20, FLOOR + 3 + z, P)} tone="faint" />)}</>} />
      <Line d={k.ring(cx, cy, 16.5, FLOOR + 55, P, 48)} tone="lo" />
      <Dots points={Array.from({ length: 10 }, (_, i) => k.iso([cx + 18.6 * Math.cos((i / 10) * Math.PI * 2), cy + 18.6 * Math.sin((i / 10) * Math.PI * 2), FLOOR + 55], P))} size={0.45} tone="mid" />
    </Part>
  );
}

function faceRect(x: number, y0: number, y1: number, z0: number, z1: number) {
  return k.pathOf([k.iso([x, y0, z0], P), k.iso([x, y1, z0], P), k.iso([x, y1, z1], P), k.iso([x, y0, z1], P)], true);
}

function Rack() {
  const plan: k.Plan = { x: 128, y: -56, w: 40, d: 48, r: 1.4 };
  const face = plan.x + plan.w;
  const units = [0, 1, 2, 3, 4, 5, 6];
  return (
    <Part id="control-electronics">
      <path className="iso-halo" d={k.haloOf(plan, FLOOR, 4, P)} />
      <Solid paths={k.slabOf(plan, FLOOR, 104, P, 3, 0.8)} tone="mid" inner={<Line d={k.sideSeam(plan, FLOOR + 4, P, 3)} tone="faint" />} />
      {units.map((u) => {
        const z0 = FLOOR + 10 + u * 13;
        return (
          <g key={u}>
            <Line d={faceRect(face + 0.05, plan.y + 3, plan.y + plan.d - 3, z0, z0 + 11)} tone="lo" />
            <Dots points={[k.iso([face + 0.1, plan.y + 5.5, z0 + 5.5], P), k.iso([face + 0.1, plan.y + plan.d - 5.5, z0 + 5.5], P)]} size={0.45} tone="mid" />
            <Line d={k.sideRing([face + 0.1, plan.y + 12 + (u % 3) * 6, z0 + 5.5], 1.4, "x", P, 14)} tone="mid" />
            <Line d={k.segment([face + 0.1, plan.y + 26, z0 + 4], [face + 0.1, plan.y + 40, z0 + 4], P)} tone="faint" />
          </g>
        );
      })}
      <Vents P={P} x={plan.x + 6} y={plan.y + 8} z={FLOOR + 104} count={9} gap={3.4} length={12} />
      <Lamp P={P} at={[plan.x + 32, plan.y + 40]} z={FLOOR + 104} status="lit" r={2} />
    </Part>
  );
}

function ReadoutBox() {
  const plan: k.Plan = { x: 128, y: 2, w: 40, d: 32, r: 1.4 };
  const face = plan.x + plan.w;
  return (
    <Part id="readout-electronics">
      <path className="iso-halo" d={k.haloOf(plan, FLOOR, 4, P)} />
      <Solid paths={k.slabOf(plan, FLOOR, 44, P, 3, 0.8)} tone="hi" inner={<Line d={k.sideSeam(plan, FLOOR + 22, P, 3)} tone="faint" />} />
      {[0, 1, 2].map((i) => (
        <Line key={i} d={k.sideRing([face + 0.1, plan.y + 8 + i * 8, FLOOR + 34], 2.4, "x", P, 18)} tone="mid" />
      ))}
      <Line d={faceRect(face + 0.05, plan.y + 4, plan.y + 28, FLOOR + 8, FLOOR + 18)} tone="lo" />
      <Dots points={[0, 1, 2, 3].map((i) => k.iso([face + 0.1, plan.y + 7 + i * 6, FLOOR + 13], P))} size={0.6} tone="hi" />
    </Part>
  );
}

function Computer() {
  const zt = FLOOR + 44;
  const body: k.Plan = { x: 134, y: 9, w: 14, d: 22, r: 1 };
  return (
    <Part id="computer">
      <Solid paths={k.slabOf({ x: 137, y: 16, w: 8, d: 8, r: 1 }, zt, 4, P, 2)} tone="mid" />
      <Solid paths={k.slabOf(body, zt + 4, 20, P, 3, 0.6)} tone="hi" />
      <Line d={faceRect(body.x + body.w + 0.05, body.y + 2.5, body.y + body.d - 2.5, zt + 7, zt + 21)} tone="mid" />
      <Solid paths={k.slabOf({ x: 152, y: 8, w: 10, d: 24, r: 0.8 }, zt, 1.4, P, 2)} tone="mid" />
      <Line d={k.planOutline({ x: 153.5, y: 9.5, w: 7, d: 21, r: 0.4 }, zt + 1.4, P, 2)} tone="faint" />
    </Part>
  );
}

function IO() {
  const z = top(STAGE_GEO[0]);
  const ports = [...CONTROL, READOUT].sort((a, b) => depth(a) - depth(b));
  return (
    <Part id="io">
      {ports.map((p, i) => (
        <React.Fragment key={i}>
          <Solid paths={k.cylinder(p[0], p[1], 3, z, 2, P, 18)} tone="mid" />
          <Solid paths={k.cylinder(p[0], p[1], 1.8, z + 2, 4, P, 16)} tone="hi" />
        </React.Fragment>
      ))}
    </Part>
  );
}

function Cables() {
  const z = top(STAGE_GEO[0]) + 6;
  const high = 284;
  return (
    <g>
      {CONTROL.map((c, i) => (
        <Part key={i} id="io">
          <Wire from={k.iso([c[0], c[1], z], P)} via={[k.iso([c[0], c[1], high - i * 4], P), k.iso([140 + i * 8, -40, high - i * 4], P)]} to={k.iso([140 + i * 8, -40, FLOOR + 104], P)} tone="mid" size={1} />
        </Part>
      ))}
      <Part id="io">
        <Wire from={k.iso([READOUT[0], READOUT[1], z], P)} via={[k.iso([READOUT[0], READOUT[1], high - 10], P), k.iso([160, 12, high - 10], P)]} to={k.iso([160, 12, FLOOR + 44], P)} tone="mid" size={1} />
      </Part>
      <Part id="computer">
        <Wire from={k.iso([134, 20, FLOOR + 60], P)} via={[k.iso([130, 20, FLOOR + 66], P)]} to={k.iso([130, -8, FLOOR + 66], P)} tone="lo" size={0.9} />
      </Part>
    </g>
  );
}

export function QuantumScene() {
  const stages = STAGE_GEO;
  return (
    <g>
      <Part id="shielding">
        <BasePlate P={P} plan={BASE} z={0} height={FLOOR} feet={6} />
        <Frame front={false} />
      </Part>
      {/* bottom up: package under the mixing chamber, then each plate with what stands on it */}
      <Package />
      {[5, 4, 3, 2, 1].map((i) => (
        <React.Fragment key={i}>
          <Part id="cryostat">
            <Plate s={stages[i]} />
          </Part>
          <Level lower={stages[i]} upper={stages[i - 1]} index={5 - i} />
        </React.Fragment>
      ))}
      <Part id="cryostat">
        <Plate s={stages[0]} tone="mid" />
      </Part>
      <IO />
      <Part id="shielding">
        <Frame front />
        <TopFrame />
      </Part>
      <ShieldCan />
      <Rack />
      <ReadoutBox />
      <Computer />
      <Cables />
    </g>
  );
}
