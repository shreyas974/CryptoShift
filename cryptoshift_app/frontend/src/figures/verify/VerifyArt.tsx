// Fig 04: an inspection line. The candidate patch rides a carriage along a rail past one station per
// check; the carriage rests at the first station it cannot clear, so where it stops is the verdict.
// A failed station sends nothing forward. The approval key switch and the release barrier stay
// mechanically closed until the stations before them have cleared.
import * as React from "react";
import * as k from "../../anatomy/kit/iso-kit";
import { Solid, Line, Dots, Wire } from "../../anatomy/kit/react/draw";
import { BasePlate, Lamp, Module, Part, Post, Ruler, Screws } from "../../anatomy/parts";
import type { Station, StationId } from "./model";

export const W = 760;
export const H = 500;
const BENCH: k.Plan = { x: 0, y: 0, w: 424, d: 76, r: 4 };
const PED_Y = 4;
const PED_D = 18;
const PED_H = 12;
const RAIL_Y = [38, 50];
const RAIL_TOP = 3;
export const LINE: StationId[] = ["diff", "build", "tests", "vectors", "protocol", "report", "approval", "release"];
export const XS: Record<StationId, number> = {
  legacy: 22,
  candidate: 22,
  ...Object.fromEntries(LINE.map((id, i) => [id, 64 + i * 40])),
  rollback: 398,
} as Record<StationId, number>;
export const CARRIAGE_END = 64 + 7 * 40 + 30;

export const P = k.fitProjection(
  [
    [BENCH.x - 8, BENCH.y - 8, -6],
    [BENCH.x + BENCH.w + 8, BENCH.y - 8, -6],
    [BENCH.x - 8, BENCH.y + BENCH.d + 8, -6],
    [BENCH.x + BENCH.w + 8, BENCH.y + BENCH.d + 8, -6],
    [BENCH.x, BENCH.y, 64],
    [BENCH.x + BENCH.w, BENCH.y, 64],
  ],
  W,
  H,
  { pad: 12, azimuth: 40, elevation: 34 },
);

export const carriageX = (stop: number) => (stop >= LINE.length ? CARRIAGE_END : XS[LINE[stop]]);

export function anchorOf(id: StationId, carriage: number): [number, number] {
  if (id === "candidate") return k.iso([carriage, 44, RAIL_TOP + 14], P);
  if (id === "release") return k.iso([XS.release, 14, 34], P);
  return k.iso([XS[id], PED_Y + PED_D / 2, PED_H + 12], P);
}

function Pedestal({ x, status }: { x: number; status: string }) {
  const plan: k.Plan = { x: x - 15, y: PED_Y, w: 30, d: PED_D, r: 1.4 };
  return (
    <g>
      <Module P={P} plan={plan} z={0} height={PED_H} tone="mid" seams={[3]} />
      <Lamp P={P} at={[x + 11, PED_Y + PED_D - 4]} z={PED_H} status={status} r={2.6} />
    </g>
  );
}

const T = PED_H;
const C = PED_Y + PED_D / 2;

function Instrument({ id, station }: { id: StationId; station: Station }) {
  const x = XS[id];
  switch (id) {
    case "legacy":
      return (
        <g>
          <Solid paths={k.slabOf({ x: x - 10, y: C - 6, w: 3, d: 12, r: 0.4 }, T, 4, P, 2)} tone="mid" />
          <Solid paths={k.slabOf({ x: x + 5, y: C - 6, w: 3, d: 12, r: 0.4 }, T, 4, P, 2)} tone="mid" />
          <Solid paths={k.slabOf({ x: x - 7, y: C - 5.5, w: 12, d: 11, r: 0.8 }, T + 1, 8, P, 3, 0.6)} tone="mid" inner={<Line d={k.sideSeam({ x: x - 7, y: C - 5.5, w: 12, d: 11, r: 0.8 }, T + 6, P, 3)} tone="faint" />} />
          <Dots points={[k.iso([x - 1, C, T + 9], P)]} size={0.6} tone="mid" />
        </g>
      );
    case "diff":
      return (
        <g>
          <Post P={P} at={[x - 8, C - 3]} z0={T} z1={T + 22} r={1.3} />
          <Solid paths={k.slabOf({ x: x - 9, y: C - 4, w: 2, d: 18, r: 0.5 }, T + 22, 1.8, P, 2)} tone="mid" />
          {/* the loupe: a lens in a ring on the arm's end, over the carriage's path */}
          <Solid paths={k.cylinder(x - 8, C + 16, 6.4, T + 20.6, 1.4, P, 40)} tone="mid" />
          <Solid paths={k.cylinder(x - 8, C + 16, 5.2, T + 22, 0.4, P, 40)} tone="hi" lit={station.status === "passed"} />
          <Line d={k.ring(x - 8, C + 16, 3.6, T + 22.4, P, 32)} tone="faint" />
          <Solid paths={k.cylinder(x + 6, C - 2, 3, T, 4, P, 20)} tone="mid" />
          <Line d={k.knurl(x + 6, C - 2, 3, T, T + 4, 16, P)} tone="lo" />
        </g>
      );
    case "build":
      return (
        <g>
          <Post P={P} at={[x - 9, C]} z0={T} z1={T + 24} r={1.4} />
          <Post P={P} at={[x + 7, C]} z0={T} z1={T + 24} r={1.4} />
          <Solid paths={k.slabOf({ x: x - 4.5, y: C - 3.5, w: 7, d: 7, r: 0.6 }, T + 9, 13, P, 2, 0.4)} tone="hi" />
          <Solid paths={k.slabOf({ x: x - 13, y: C - 5, w: 24, d: 10, r: 1 }, T + 24, 5, P, 3, 0.8)} tone="mid" />
          <Screws P={P} plan={{ x: x - 13, y: C - 5, w: 24, d: 10, r: 1 }} z={T + 29} inset={2.4} r={0.7} />
          <Solid paths={k.slabOf({ x: x - 6, y: C - 5, w: 10, d: 10, r: 0.6 }, T, 1.6, P, 2)} tone="lo" />
        </g>
      );
    case "tests":
      return (
        <g>
          <Solid paths={k.slabOf({ x: x - 11, y: C - 6, w: 20, d: 11, r: 1 }, T, 10, P, 3, 0.8)} tone="hi" inner={<Line d={k.sideSeam({ x: x - 11, y: C - 6, w: 20, d: 11, r: 1 }, T + 3, P, 3)} tone="faint" />} />
          {/* a row of spring probes reaching toward the rail */}
          {[-8, -4, 0, 4].map((dx) => (
            <React.Fragment key={dx}>
              <Solid paths={k.slabOf({ x: x + dx - 0.6, y: C + 5, w: 1.2, d: 11, r: 0.4 }, T + 4.6, 1.2, P, 2)} tone="mid" />
              <Dots points={[k.iso([x + dx, C + 16.2, T + 5.8], P)]} size={0.55} tone="hi" />
            </React.Fragment>
          ))}
          <Line d={k.planOutline({ x: x - 8, y: C - 3.5, w: 14, d: 6, r: 0.6 }, T + 10, P, 3)} tone="lo" />
        </g>
      );
    case "vectors": {
      // gauge blocks: reference sizes the provider's declared sizes are measured against
      const blocks = [4, 7, 10, 13, 16];
      return (
        <g>
          <Solid paths={k.slabOf({ x: x - 12, y: C - 6, w: 22, d: 12, r: 0.8 }, T, 1.6, P, 2)} tone="lo" />
          {blocks.map((h, i) => (
            <Solid key={i} paths={k.slabOf({ x: x - 11 + i * 4.2, y: C - 4.5, w: 3.4, d: 9, r: 0.3 }, T + 1.6, h, P, 2, 0.3)} tone={i === blocks.length - 1 ? "hi" : "mid"} />
          ))}
        </g>
      );
    }
    case "protocol":
      return (
        <g>
          {/* a socket and a plug: the two ends of a handshake, joined by their lead */}
          <Solid paths={k.cylinder(x - 7, C, 5, T, 9, P, 32, 0.6)} tone="mid" />
          <Line d={k.ring(x - 7, C, 3, T + 9, P, 24)} tone="lo" />
          <Dots points={[k.iso([x - 8.2, C, T + 9], P), k.iso([x - 5.8, C, T + 9], P)]} size={0.5} tone="hi" />
          <Solid paths={k.cylinder(x + 6, C, 3.4, T, 13, P, 28, 0.5)} tone="hi" />
          <Solid paths={k.cylinder(x + 6, C, 2, T + 13, 2, P, 20)} tone="mid" />
          <Wire from={k.iso([x - 7, C + 3, T + 9], P)} via={[k.iso([x - 1, C + 3, T + 16], P)]} to={k.iso([x + 6, C, T + 15], P)} tone="mid" size={0.9} />
        </g>
      );
    case "report":
      return (
        <g>
          <Solid paths={k.slabOf({ x: x - 11, y: C - 7, w: 22, d: 13, r: 1.2 }, T, 9, P, 3, 0.8)} tone="hi" inner={<Line d={k.sideSeam({ x: x - 11, y: C - 7, w: 22, d: 13, r: 1.2 }, T + 3, P, 3)} tone="faint" />} />
          <Line d={k.planOutline({ x: x - 8.5, y: C - 3, w: 17, d: 1.6, r: 0.6 }, T + 9, P, 2)} tone="lo" />
          {station.status !== "unrun" ? (
            <g>
              {/* the printed report, standing out of the slot */}
              <Solid paths={k.slabOf({ x: x - 8, y: C - 2.6, w: 16, d: 0.6, r: 0 }, T + 9, 15, P, 1)} tone="hi" crease="none" lit />
              {[0, 1, 2, 3].map((i) => (
                <Line key={i} d={k.segment([x - 6.2, C - 2, T + 21 - i * 3], [x + (i === 3 ? 0 : 5), C - 2, T + 21 - i * 3], P)} tone="lo" free />
              ))}
            </g>
          ) : null}
        </g>
      );
    case "approval": {
      const open = station.status === "passed";
      return (
        <g>
          <Solid paths={k.cylinder(x - 1, C, 7, T, 6, P, 40, 0.8)} tone="mid" />
          <Line d={k.radialTicks(x - 1, C, 6.6, 8, 4, T + 6, [0.8, 1.6], P).major} tone="lo" />
          <Solid paths={k.cylinder(x - 1, C, 3.4, T + 6, 2, P, 28)} tone="hi" />
          {/* the key: across the slot when locked, turned a quarter when approved */}
          <Solid paths={k.slabOf(open ? { x: x - 1.8, y: C - 6, w: 1.6, d: 12, r: 0.4 } : { x: x - 7, y: C - 0.8, w: 12, d: 1.6, r: 0.4 }, T + 8, 6, P, 2)} tone="hi" lit={station.status === "pending"} />
          <Line d={k.ring(x - 1, C, 1.2, T + 8, P, 12)} tone="mid" />
        </g>
      );
    }
    case "release":
      return (
        <g>
          <Solid paths={k.slabOf({ x: x - 7, y: C - 5, w: 10, d: 10, r: 1 }, T, 8, P, 3, 0.6)} tone="hi" />
          <Post P={P} at={[x - 2, C]} z0={T + 8} z1={T + 18} r={1.6} />
          <Solid paths={k.cylinder(x - 2, C, 3, T + 18, 3, P, 24)} tone="mid" />
        </g>
      );
    case "rollback":
      return (
        <g>
          {/* the recovery bin: holds the stored original when a checkpoint exists */}
          <Solid paths={k.slabOf({ x: x - 12, y: C - 7, w: 22, d: 14, r: 1 }, T, 9, P, 3, 0.6)} tone="mid" />
          <path className="ax-tray" d={k.planOutline({ x: x - 10.5, y: C - 5.5, w: 19, d: 11, r: 0.6 }, T + 9, P, 3)} />
          {station.status !== "unrun" ? <Solid paths={k.slabOf({ x: x - 7, y: C - 3.5, w: 12, d: 7, r: 0.6 }, T + 9, 2.4, P, 3)} tone="hi" /> : null}
        </g>
      );
    default:
      return null;
  }
}

/** The barrier arm is drawn after the carriage: it reaches across the rail above it. */
export function BarrierArm({ raised }: { raised: boolean }) {
  const x = XS.release;
  const z = T + 19;
  const arm: k.Plan = raised ? { x: x - 3, y: C - 1, w: 2, d: 2, r: 0.4 } : { x: x - 3, y: C + 2, w: 2, d: 54, r: 0.6 };
  const bands = raised ? [] : [14, 24, 34, 44];
  return (
    <g>
      <Solid paths={k.slabOf(arm, z, raised ? 34 : 2, P, 2)} tone="hi" />
      {bands.map((b) => (
        <Line key={b} d={k.pathOf([k.iso([x - 1, C + 2 + b, z + 2], P), k.iso([x - 1, C + 2 + b + 4, z + 2], P), k.iso([x - 1, C + 2 + b + 4, z], P)])} tone="red" />
      ))}
    </g>
  );
}

export function LineBench() {
  return (
    <g key="bench">
      <BasePlate P={P} plan={BENCH} z={-6} height={6} feet={6} />
      <Ruler P={P} from={BENCH.x + 10} to={BENCH.x + BENCH.w - 10} y={BENCH.y + BENCH.d - 10} z={0} step={5} />
    </g>
  );
}

export function Rail() {
  return (
    <g key="rail">
      {/* sleepers, then the two rails, then end stops */}
      {Array.from({ length: 11 }, (_, i) => (
        <Solid key={i} paths={k.slabOf({ x: 14 + i * 38, y: 34, w: 4, d: 22, r: 0.5 }, 0, 1, P, 2)} tone="lo" crease="none" />
      ))}
      {RAIL_Y.map((y) => (
        <Solid key={y} paths={k.slabOf({ x: 10, y: y - 1.5, w: 404, d: 3, r: 0.6 }, 0, RAIL_TOP, P, 2, 0.4)} tone="mid" />
      ))}
      {[8, 412].map((x) => (
        <Solid key={x} paths={k.slabOf({ x, y: 34, w: 4, d: 22, r: 0.8 }, 0, 7, P, 3, 0.6)} tone="mid" />
      ))}
    </g>
  );
}

export function Carriage({ x, status }: { x: number; status: string }) {
  const base: k.Plan = { x: x - 12, y: 36, w: 24, d: 16, r: 1.2 };
  const wheels: k.Plane[] = [
    [x - 8, 38],
    [x + 8, 38],
    [x - 8, 50],
    [x + 8, 50],
  ];
  return (
    <g>
      <path className="iso-halo" d={k.haloOf(base, RAIL_TOP, 4, P)} />
      {wheels
        .sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P))
        .map(([wx, wy], i) => (
          <Solid key={i} paths={k.cylinder(wx, wy, 2.4, RAIL_TOP, 2, P, 20)} tone="lo" />
        ))}
      <Solid paths={k.slabOf(base, RAIL_TOP + 2, 3, P, 3, 0.6)} tone="mid" />
      <Screws P={P} plan={base} z={RAIL_TOP + 5} inset={2.2} r={0.7} />
      {/* the candidate patch cartridge: the one lit part */}
      <Solid paths={k.slabOf({ x: x - 7, y: 38.5, w: 14, d: 11, r: 0.8 }, RAIL_TOP + 5, 8, P, 3, 0.6)} tone="hi" lit inner={<Line d={k.sideSeam({ x: x - 7, y: 38.5, w: 14, d: 11, r: 0.8 }, RAIL_TOP + 10, P, 3)} tone="faint" />} />
      <Lamp P={P} at={[x + 3, 46]} z={RAIL_TOP + 13} status={status} r={1.6} />
    </g>
  );
}

export function Stations({ stations }: { stations: Station[] }) {
  const back = stations.filter((s) => s.id !== "candidate").sort((a, b) => XS[a.id] - XS[b.id]);
  return (
    <g key="stations">
      {back.map((s) => (
        <Part key={s.id} id={s.id} state={s.status}>
          <Pedestal x={XS[s.id]} status={s.status === "neutral" ? "unrun" : s.status === "blocked" ? "failed" : s.status} />
          <Instrument id={s.id} station={s} />
        </Part>
      ))}
    </g>
  );
}

export function VerifyPreview({ stations, carriage }: { stations: Station[]; carriage: number }) {
  const release = stations.find((s) => s.id === "release");
  return (
    <g>
      <LineBench />
      <Stations stations={stations} />
      <Rail />
      <Carriage x={carriage} status="pending" />
      <BarrierArm raised={release?.status === "passed"} />
    </g>
  );
}
