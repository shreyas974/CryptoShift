import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { axisVector } from "./iso/iso-kit";
import { Dots, IsoFigure, Line, Plate, Solid } from "./iso/react/draw";
import { useInView, useStillness } from "./iso/react/live";
import * as G from "./pipeline/geometry";
import "./iso/iso.css";
import "./pipeline/pipeline.css";

export interface PipelineService {
  id: string;
  wave: number;
  state: string; // READY | PROPOSED | APPROVED | unknown (from the backend, never invented)
}

export interface PipelineFigureProps {
  services: PipelineService[];
  findings: number;
  objective: number | null;
  readyCount: number;
  approvedCount: number;
  theme: "dark" | "light";
  reduceMotion: boolean;
}

const TOUR_MS = 2600;
const RESUME_TICKS = 3; // tour pauses for 3 tour steps after the reader picks a crate

/**
 * Fig. 1 "Sorting line": decorative, explanatory illustration (anatomy kit). It is NOT evidence; every number in its
 * readout comes from props that carry the backend's real report data.
 */
export function PipelineFigure({
  services,
  findings,
  objective,
  readyCount,
  approvedCount,
  theme,
  reduceMotion,
}: PipelineFigureProps) {
  const ordered = useMemo(() => [...services].sort((a, b) => a.wave - b.wave || a.id.localeCompare(b.id)), [services]);
  const crates = useMemo(() => G.cratesOf(ordered), [ordered]);
  const waves = useMemo(() => Math.max(1, ...ordered.map((s) => s.wave + 1)), [ordered]);
  const dividers = useMemo(() => G.waveDividers(waves), [waves]);
  const [active, setActive] = useState(0);
  const pausedTicks = useRef(0);
  const stageRef = useRef<HTMLDivElement>(null);
  const inView = useInView(stageRef);
  const still = useStillness() || reduceMotion;

  useEffect(() => {
    if (still || !inView || ordered.length < 2) return;
    const id = window.setInterval(() => {
      if (pausedTicks.current > 0) {
        pausedTicks.current -= 1;
        return;
      }
      setActive((a) => (a + 1) % ordered.length);
    }, TOUR_MS);
    return () => window.clearInterval(id);
  }, [still, inView, ordered.length]);

  const choose = (i: number) => {
    pausedTicks.current = RESUME_TICKS;
    setActive(((i % ordered.length) + ordered.length) % ordered.length);
  };
  const onKey = (e: KeyboardEvent) => {
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      choose(active + 1);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      choose(active - 1);
    }
  };

  const current = ordered[active];
  const ready = (current?.state ?? "").toUpperCase() === "READY";
  const [lx, ly] = axisVector(G.P, [0, 0, ready ? G.GATE.lift : 0]);
  const readout = current
    ? `${current.id} · wave ${current.wave} · ${(current.state || "unknown").toUpperCase()} · ${readyCount}/${ordered.length} ready · objective ${objective ?? "–"}`
    : "no plan loaded";
  const label = `Illustration of the CryptoShift migration line: ${ordered.length} service crates in ${waves} scheduled waves pass an inventory scanner, a verification gate, a human approval stamp and a rollback vault. ${readyCount} of ${ordered.length} steps are READY; ${approvedCount} approved.`;

  // painter's layers: base -> conveyor and back structure -> crates (by depth) -> front structure -> gate -> vault
  const back = [G.SCAN.postBack, G.STAMP.column, G.STAMP.pad, ...dividers.back].sort(G.byDepth);
  const front = [G.RAIL_FRONT_PART, ...dividers.front, G.SCAN.postFront].sort(G.byDepth);
  const crateOrder = crates.map((c, i) => ({ c, i, depth: c.body.depth })).sort(G.byDepth);

  return (
    <div className="iso pl-figure" data-theme={theme}>
      <Plate
        fig="Fig. 1"
        title="Sorting line"
        hint="Hover or click a crate · arrow keys"
        readout={readout}
        keys={[
          { label: "service crate (one per real service)", mark: "raised" },
          { label: "selected crate", mark: "lit" },
          { label: "gate boom up = step READY", mark: "edge" },
        ]}
        caption={`Decorative explanation, not evidence. Crates sit in the waves chosen by the scheduler; the gate lifts only for READY steps; the stamp stays up until a human approves (${approvedCount} approved). ${findings} findings were scanned.`}
      >
        <div
          ref={stageRef}
          tabIndex={0}
          onKeyDown={onKey}
          aria-label="Pipeline figure; use arrow keys to step through services"
          className="pl-stage"
          data-still={still ? "" : undefined}
        >
          <IsoFigure width={G.WIDTH} height={G.HEIGHT} label={label}>
            {/* base */}
            {G.FEET.map((f) => (
              <Solid key={f.key} paths={f.paths} tone={f.tone} />
            ))}
            <Solid paths={G.BASE_PART.paths} tone="lo" halo inner={<Line d={G.GROOVE} tone="faint" />} />
            <Dots points={G.SCREWS} size={0.9} tone="mid" />
            <Solid paths={G.LABEL_PART.paths} tone="mid" />
            {G.LABEL_RULES.map((d, i) => (
              <Line key={i} d={d} tone="faint" free />
            ))}
            <Dots points={G.LABEL_SCREWS} size={0.5} tone="mid" />
            <Solid paths={G.RULER_PART.paths} tone="mid" />
            <Line d={G.RULER_TICKS.minor} tone="lo" />
            <Line d={G.RULER_TICKS.major} tone="mid" />
            {/* conveyor + back structure */}
            <Solid paths={G.BED_PART.paths} tone="mid" />
            <Solid paths={G.BELT_PART.paths} tone="lo" />
            {G.BELT_SEAMS.map((d, i) => (
              <Line key={`bs${i}`} d={d} tone="faint" />
            ))}
            <Solid paths={G.RAIL_BACK_PART.paths} tone="mid" />
            {back.map((p) => (
              <Solid key={p.key} paths={p.paths} tone={p.tone} />
            ))}
            <Solid paths={G.STAMP.arm.paths} tone="mid" />
            <g className="pl-plunger" data-pressed={approvedCount > 0 ? "" : undefined}>
              <Solid paths={G.STAMP.plunger.paths} tone="hi" />
            </g>
            <Solid paths={G.STAMP.knob} tone="mid" />
            {/* crates, far to near */}
            {crateOrder.map(({ c, i }) => {
              const svc = ordered[i];
              const lit = i === active;
              return (
                <g
                  key={c.id}
                  className="pl-crate"
                  data-state={(svc?.state ?? "unknown").toUpperCase()}
                  onPointerEnter={() => choose(i)}
                  onClick={() => choose(i)}
                >
                  <Solid paths={c.body.paths} tone="hi" lit={lit} inner={<Line d={c.lid} tone="faint" />} />
                  <Solid paths={c.lamp} tone={(svc?.state ?? "").toUpperCase() === "READY" ? "hi" : "faint"} />
                  <Dots points={c.corners} size={0.45} tone="mid" />
                  {c.plate.map((d, k) => (
                    <Line key={k} d={d} tone="faint" free />
                  ))}
                </g>
              );
            })}
            {/* front structure */}
            {front.map((p) => (
              <Solid key={p.key} paths={p.paths} tone={p.tone} />
            ))}
            <Dots points={G.RAIL_SCREWS} size={0.45} tone="mid" />
            <Dots points={dividers.caps} size={0.9} tone="hi" />
            <Solid paths={G.SCAN.bar.paths} tone="mid" />
            <Dots points={G.SCAN.barScrews} size={0.55} tone="mid" />
            <Solid paths={G.SCAN.head.paths} tone="hi" />
            <Line d={G.SCAN.lens} tone="mid" />
            {/* verification gate: the boom lifts only when the selected step is READY */}
            <g className="pl-boom" style={{ transform: `translate(${lx}px, ${ly}px)` }}>
              <Solid paths={G.GATE.boom} tone="hi" lit={ready} />
              {G.GATE.boomStripes.map((d, i) => (
                <Line key={i} d={d} tone="mid" />
              ))}
            </g>
            <Solid paths={G.GATE.post.paths} tone="mid" />
            <Solid paths={G.GATE.postCap} tone="hi" />
            {/* rollback vault */}
            <Solid paths={G.VAULT_GEO.body.paths} tone="mid" inner={<Line d={G.VAULT_GEO.seam} tone="faint" />} />
            <Line d={G.VAULT_GEO.dialRing} tone="mid" />
            <Line d={G.VAULT_GEO.dialTicks.minor} tone="lo" />
            <Line d={G.VAULT_GEO.dialTicks.major} tone="mid" />
            <Solid paths={G.VAULT_GEO.knob} tone="hi" />
            <Dots points={G.VAULT_GEO.screws} size={0.5} tone="mid" />
          </IsoFigure>
        </div>
        <ul className="sr-only">
          {ordered.map((s) => (
            <li key={s.id}>
              {s.id}: wave {s.wave}, {(s.state || "unknown").toUpperCase()}
            </li>
          ))}
        </ul>
      </Plate>
    </div>
  );
}
