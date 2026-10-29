// Fig 02: an evidence cabinet. Ten drawers, one per field of a scanned finding. A drawer's pip shows
// how the field is known (solid: declared or detected, ring: inferred, dashed: unknown). The selected
// drawer slides out and shows one index card per piece of evidence. The dial on top reads the risk score.
import * as k from "../../anatomy/kit/iso-kit";
import { Solid, Line, Dots } from "../../anatomy/kit/react/draw";
import { BasePlate, LabelPlate, Part, Screws } from "../../anatomy/parts";
import type { AssetField, FieldId } from "./model";
import type { Plan, Point3 } from "../../anatomy/kit/iso-kit";

export const W = 640;
export const H = 470;

const BODY: Plan = { x: 0, y: 0, w: 60, d: 124, r: 1.2 };
const Z0 = 10;
const Z1 = 162;
const FACE = BODY.x + BODY.w;
const PULL = 34;
const ROW_H = 28;
const ROWS = 5;
const COLS = [
  { y: 4, d: 55 },
  { y: 65, d: 55 },
];
export const ORDER: FieldId[] = ["repository", "evidence", "algorithm", "role", "context", "dependencies", "exposure", "risk", "recommendation", "verification"];

export const P = k.fitProjection(
  [
    [-6, -6, -6],
    [FACE + PULL + 4, -6, -6],
    [-6, 130, -6],
    [FACE + PULL + 4, 130, -6],
    [30, 62, Z1 + 16],
    [0, 0, Z1 + 16],
    [60, 124, Z1 + 16],
  ],
  W,
  H,
  { pad: 14, azimuth: 35 },
);

export interface Slot {
  id: FieldId;
  col: number;
  row: number;
  y: number;
  d: number;
  z: number;
  h: number;
}

export const SLOTS: Slot[] = ORDER.map((id, i) => {
  const col = i < 5 ? 0 : 1;
  const row = i % 5;
  const z = Z0 + 6 + (ROWS - 1 - row) * ROW_H;
  return { id, col, row, y: COLS[col].y, d: COLS[col].d, z, h: ROW_H - 3 };
});

export const anchorFor = (id: FieldId, open: boolean): [number, number] => {
  const s = SLOTS.find((x) => x.id === id)!;
  if (id === "risk" && !open) return k.iso([30, 40, Z1 + 9], P);
  return k.iso([FACE + 2.2 + (open ? PULL : 0), s.y + s.d / 2, s.z + s.h - 4], P);
};

// ---------- static cabinet ----------
const DIAL = { cx: 30, cy: 42, r: 21 };
const SPAN = Math.PI * 1.5;
const FROM = -Math.PI * 0.75;

function needlePath(score: number) {
  const a = FROM + (Math.max(0, Math.min(100, score)) / 100) * SPAN;
  const z = Z1 + 10.6;
  const tip: [number, number] = [DIAL.cx + Math.sin(a) * 15.5, DIAL.cy - Math.cos(a) * 15.5];
  const tail: [number, number] = [DIAL.cx - Math.sin(a) * 4, DIAL.cy + Math.cos(a) * 4];
  return k.lineOnTop(tail, tip, z, P);
}

function bandArc(from: number, to: number, r: number, z: number) {
  const pts: k.Flat[] = [];
  for (let i = 0; i <= 24; i++) {
    const a = FROM + ((from + ((to - from) * i) / 24) / 100) * SPAN;
    pts.push(k.iso([DIAL.cx + Math.sin(a) * r, DIAL.cy - Math.cos(a) * r, z], P));
  }
  return k.pathOf(pts);
}

export function CabinetBody() {
  const sideFace = BODY.y + BODY.d;
  return (
    <g key="cabinet">
      <BasePlate P={P} plan={{ x: -6, y: -6, w: 72, d: 136, r: 3 }} z={0} height={Z0} feet={6} />
      <Solid
        paths={k.slabOf(BODY, Z0, Z1 - Z0, P, 4, 0.8)}
        tone="mid"
        inner={
          <>
            {/* panel seams wrap the visible corner at three heights */}
            <Line d={k.sideSeam(BODY, Z0 + 4, P, 4)} tone="faint" />
            <Line d={k.sideSeam(BODY, Z1 - 4, P, 4)} tone="faint" />
            {/* centre stile between the two drawer columns runs the full face */}
            <Line d={k.segment([FACE, 62, Z0 + 4], [FACE, 62, Z1 - 4], P)} tone="faint" />
            {/* side panel: two recessed carry handles and a rivet row */}
            {[40, 100].map((x) => (
              <Line key={x} d={k.pathOf([k.iso([x - 9, sideFace, Z1 - 30], P), k.iso([x + 9, sideFace, Z1 - 30], P), k.iso([x + 9, sideFace, Z1 - 34], P), k.iso([x - 9, sideFace, Z1 - 34], P)], true)} tone="lo" />
            ))}
          </>
        }
      />
      <Dots points={[0.1, 0.3, 0.5, 0.7, 0.9].map((s) => k.iso([BODY.w * s, sideFace, Z0 + 8], P))} size={0.45} tone="mid" />
      <Dots points={[0.1, 0.3, 0.5, 0.7, 0.9].map((s) => k.iso([BODY.w * s, sideFace, Z1 - 8], P))} size={0.45} tone="mid" />
      {/* drawer openings: each a recess outline on the face */}
      {SLOTS.map((s) => (
        <Line key={s.id} d={k.pathOf([k.iso([FACE, s.y - 0.8, s.z - 0.8], P), k.iso([FACE, s.y + s.d + 0.8, s.z - 0.8], P), k.iso([FACE, s.y + s.d + 0.8, s.z + s.h + 0.8], P), k.iso([FACE, s.y - 0.8, s.z + s.h + 0.8], P)], true)} tone="lo" />
      ))}
      {/* top cap */}
      <Solid paths={k.slabOf({ x: -2, y: -2, w: 64, d: 128, r: 2 }, Z1, 3, P, 4, 1.2)} tone="mid" />
      <Screws P={P} plan={{ x: -2, y: -2, w: 64, d: 128, r: 2 }} z={Z1 + 3} inset={4} r={1.2} />
      <LabelPlate P={P} plan={{ x: 14, y: 82, w: 32, d: 30, r: 1.2 }} z={Z1 + 3} />
    </g>
  );
}

export function RiskDial({ score }: { score: number | null }) {
  const z = Z1 + 3;
  const ticks = k.radialTicks(DIAL.cx, DIAL.cy, 18, 20, 5, z + 7.4, [1.6, 3], P, FROM, SPAN);
  return (
    <g key="dial">
      <Solid paths={k.cylinder(DIAL.cx, DIAL.cy, DIAL.r + 2, z, 2.4, P, 48)} tone="lo" halo />
      <Solid paths={k.cylinder(DIAL.cx, DIAL.cy, DIAL.r, z + 2.4, 3, P, 48, 0.8)} tone="mid" />
      <Solid paths={k.cylinder(DIAL.cx, DIAL.cy, DIAL.r - 1.6, z + 5.4, 2, P, 48)} tone="hi" />
      <Line d={ticks.minor} tone="lo" />
      <Line d={ticks.major} tone="mid" />
      <Line d={bandArc(70, 100, 13.4, z + 7.4)} tone="red" />
      <Line d={bandArc(50, 70, 13.4, z + 7.4)} tone="mid" />
      {score != null ? <Line d={needlePath(score)} tone="lit" className="ax-needle" /> : null}
      <Solid paths={k.cylinder(DIAL.cx, DIAL.cy, 1.8, z + 7.4, 1.4, P, 20)} tone="hi" />
      {/* knurled zero-adjust knob at the dial's rim */}
      <Solid paths={k.cylinder(DIAL.cx + 22, DIAL.cy + 14, 3, z, 5, P, 24)} tone="mid" />
      <Line d={k.knurl(DIAL.cx + 22, DIAL.cy + 14, 3, z, z + 5, 18, P)} tone="lo" />
    </g>
  );
}

// ---------- drawers ----------
function rect(x: number, y0: number, y1: number, z0: number, z1: number) {
  return k.pathOf([k.iso([x, y0, z0], P), k.iso([x, y1, z0], P), k.iso([x, y1, z1], P), k.iso([x, y0, z1], P)], true);
}

export function Drawer({ slot, field, extension }: { slot: Slot; field: AssetField | null; extension: number }) {
  const e = extension;
  const { y, d, z, h } = slot;
  const front: Plan = { x: FACE + e, y, w: 2.2, d, r: 0.6 };
  const fx = FACE + 2.2 + e;
  const ym = y + d / 2;
  const basis = field?.basis ?? "unknown";
  const pip: Point3 = [fx + 0.05, y + 6, z + h - 5];
  const cards = field?.cards ?? 0;
  return (
    <Part id={slot.id} state={field?.status}>
      {e > 0.4 ? (
        <g>
          {/* drawer body: only the length outside the cabinet is visible */}
          <Solid paths={k.slabOf({ x: FACE, y: y + 1.5, w: e, d: d - 3, r: 0.4 }, z + 1, h - 5, P, 2)} tone="mid" />
          <path className="ax-tray" d={k.planOutline({ x: FACE + 0.2, y: y + 3, w: Math.max(0, e - 1.4), d: d - 6, r: 0.3 }, z + h - 4, P, 2)} />
          {Array.from({ length: cards }, (_, i) => {
            const cx = FACE + e - 5 - i * 4.6;
            if (cx < FACE + 1.5) return null;
            return <Solid key={i} paths={k.slabOf({ x: cx, y: y + 6 + (i % 2) * 3, w: 0.9, d: d - 15, r: 0.3 }, z + h - 4, 3.6 - (i % 3) * 0.6, P, 2)} tone="hi" crease="none" />;
          })}
        </g>
      ) : null}
      <Solid paths={k.slabOf(front, z, h, P, 3, 0.6)} tone="hi" />
      {/* label holder (a thin frame) and its card */}
      <Solid paths={k.slabOf({ x: fx, y: ym - 9, w: 0.5, d: 18, r: 0.2 }, z + h - 9, 6, P, 2)} tone="mid" crease="none" />
      <Line d={rect(fx + 0.55, ym - 7.6, ym + 7.6, z + h - 7.6, z + h - 4.4)} tone="faint" />
      {/* pull bar on two standoffs */}
      <Solid paths={k.slabOf({ x: fx, y: ym - 8, w: 1.6, d: 2, r: 0.4 }, z + 6, 3, P, 2)} tone="mid" />
      <Solid paths={k.slabOf({ x: fx, y: ym + 6, w: 1.6, d: 2, r: 0.4 }, z + 6, 3, P, 2)} tone="mid" />
      <Solid paths={k.slabOf({ x: fx + 1.6, y: ym - 10, w: 1.8, d: 20, r: 0.8 }, z + 5.6, 3.8, P, 4, 0.4)} tone="hi" />
      {/* evidence pip */}
      <path className="ax-pip" data-basis={field?.id === "verification" ? field.status : basis} d={k.sideRing(pip, 1.7, "x", P, 20)} />
      <Dots points={[k.iso([fx + 0.05, y + 2.4, z + 2.4], P), k.iso([fx + 0.05, y + d - 2.4, z + 2.4], P)]} size={0.35} tone="mid" />
    </Part>
  );
}

export const PULL_DISTANCE = PULL;

/** Static preview used on the Anatomy Lab card: same parts, no interaction. */
export function AssetPreview({ fields, open }: { fields: AssetField[] | null; open?: FieldId }) {
  const byId = new Map(fields?.map((f) => [f.id, f]) ?? []);
  const sorted = [...SLOTS].sort((a, b) => (a.id === open ? 1 : b.id === open ? -1 : a.col - b.col || b.row - a.row));
  const risk = byId.get("risk");
  return (
    <g>
      <CabinetBody />
      <RiskDial score={risk ? Number(risk.value.split("/")[0]) : null} />
      {sorted.map((s) => (
        <Drawer key={s.id} slot={s} field={byId.get(s.id) ?? null} extension={s.id === open ? PULL : 0} />
      ))}
    </g>
  );
}

export const assetKeys: k.LegendKey[] = [
  { mark: "raised", label: "Drawer = one field of the finding" },
  { mark: "lit", label: "Risk needle" },
  { mark: "red", label: "Critical band (70–100)" },
];

export const PipLegend = () => (
  <span className="ax-swatches">
    <span><i className="pip pip-known" /> Declared / detected</span>
    <span><i className="pip pip-inferred" /> Inferred</span>
    <span><i className="pip pip-unknown" /> Unknown</span>
  </span>
);

