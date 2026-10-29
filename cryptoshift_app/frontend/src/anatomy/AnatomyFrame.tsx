// The shared interactive frame for every anatomy figure: the Anatomy card (Plate), part selection by
// pointer, keyboard and component list, an HTML callout pinned to the selected part, a live readout,
// a guided tour, and a text fallback if the drawing fails to render.
import * as React from "react";
import { Plate } from "./kit/react/draw";
import { useStillness } from "./kit/react/live";
import type { LegendKey } from "./kit/iso-kit";

export type PartStatus = "passed" | "failed" | "pending" | "unrun" | "blocked" | "known" | "inferred" | "unknown" | "neutral";

export interface PartInfo {
  id: string;
  label: string;
  group?: string;
  summary: string;
  readout: string;
  status?: PartStatus;
  statusLabel?: string;
  anchor: [number, number];
  related?: string[];
}

interface FrameProps {
  fig: string;
  title: string;
  ariaLabel: string;
  width: number;
  height: number;
  parts: PartInfo[];
  selected: string | null;
  onSelect: (id: string | null) => void;
  idleReadout: string;
  hint?: string;
  keys?: LegendKey[];
  caption?: React.ReactNode;
  detail: React.ReactNode;
  toolbar?: React.ReactNode;
  compact?: boolean;
  children: React.ReactNode;
}

class FigureBoundary extends React.Component<{ fallback: React.ReactNode; children: React.ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(error: unknown) {
    console.error("Anatomy figure failed to render", error);
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

const TOUR_MS = 5200;

export function AnatomyFrame({ fig, title, ariaLabel, width, height, parts, selected, onSelect, idleReadout, hint, keys, caption, detail, toolbar, compact, children }: FrameProps) {
  const stage = React.useRef<HTMLDivElement>(null);
  const [touring, setTouring] = React.useState(false);
  const still = useStillness();
  const current = parts.find((p) => p.id === selected) ?? null;
  const index = current ? parts.indexOf(current) : -1;

  // Write selection and relation attributes onto the static art without re-rendering it.
  React.useEffect(() => {
    const root = stage.current;
    if (!root) return;
    const related = new Set(current?.related ?? []);
    root.querySelectorAll<SVGGElement>("[data-part]").forEach((node) => {
      const id = node.dataset.part!;
      node.toggleAttribute("data-selected", id === selected);
      node.toggleAttribute("data-related", related.has(id));
    });
    root.toggleAttribute("data-has-selection", Boolean(selected));
  }, [selected, current, children]);

  const step = React.useCallback(
    (delta: number) => {
      if (!parts.length) return;
      const next = index < 0 ? (delta > 0 ? 0 : parts.length - 1) : (index + delta + parts.length) % parts.length;
      onSelect(parts[next].id);
    },
    [index, parts, onSelect],
  );

  React.useEffect(() => {
    if (!touring) return;
    if (index < 0) step(1);
    const timer = window.setInterval(() => step(1), TOUR_MS);
    return () => window.clearInterval(timer);
  }, [touring, step, index]);

  const choose = (id: string | null) => {
    setTouring(false);
    onSelect(id);
  };

  const onKey = (event: React.KeyboardEvent) => {
    const map: Record<string, () => void> = {
      ArrowRight: () => step(1),
      ArrowDown: () => step(1),
      ArrowLeft: () => step(-1),
      ArrowUp: () => step(-1),
      Home: () => onSelect(parts[0]?.id ?? null),
      End: () => onSelect(parts[parts.length - 1]?.id ?? null),
      Escape: () => onSelect(null),
    };
    const action = map[event.key];
    if (!action) return;
    event.preventDefault();
    setTouring(false);
    action();
  };

  const partAt = (target: EventTarget | null) => (target instanceof Element ? (target.closest("[data-part]") as SVGGElement | null) : null);

  const onPointerOver = (event: React.PointerEvent) => {
    const root = stage.current;
    if (!root) return;
    const hit = partAt(event.target);
    root.querySelectorAll("[data-hover]").forEach((n) => n !== hit && n.removeAttribute("data-hover"));
    hit?.setAttribute("data-hover", "");
  };

  const fallback = (
    <div className="ax-fallback" role="note">
      The drawing could not be rendered in this browser. Every component is still listed and selectable on the right.
    </div>
  );

  const calloutSide = current && current.anchor[0] / width > 0.74 ? "left" : "right";

  return (
    <section className={compact ? "ax-frame ax-compact" : "ax-frame"} aria-label={title}>
      {toolbar || !compact ? (
        <div className="ax-toolbar">
          {toolbar}
          {!compact ? (
            <div className="ax-tour">
              <button className="btn btn-ghost" onClick={() => step(-1)} aria-label="Previous component">
                ‹
              </button>
              <button className="btn" aria-pressed={touring} onClick={() => setTouring((t) => !t)}>
                {touring ? "Stop tour" : "Guided tour"}
              </button>
              <button className="btn btn-ghost" onClick={() => step(1)} aria-label="Next component">
                ›
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
      <div className="ax-grid">
        <div className="ax-figure-col">
          <div
            ref={stage}
            className="ax-stage iso"
            data-theme="light"
            data-still={still ? "" : undefined}
            tabIndex={0}
            role="group"
            aria-label={`${ariaLabel}. Use arrow keys to move between components, Escape to clear.`}
            aria-describedby={`${fig}-parts`}
            onKeyDown={onKey}
            onPointerOver={onPointerOver}
            onPointerLeave={() => stage.current?.querySelectorAll("[data-hover]").forEach((n) => n.removeAttribute("data-hover"))}
            onClick={(event) => {
              const hit = partAt(event.target);
              choose(hit ? hit.dataset.part! : null);
            }}
          >
            <Plate fig={fig} title={title} hint={hint ?? "Select a component"} readout={current ? current.readout : idleReadout} keys={keys} caption={caption}>
              <FigureBoundary fallback={fallback}>
                <div className="ax-svg-wrap">
                  <svg className="iso-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel} focusable="false">
                    {children}
                    {current ? (
                      <g className="ax-pin" aria-hidden="true">
                        <circle cx={current.anchor[0]} cy={current.anchor[1]} r={3.2} />
                        <circle cx={current.anchor[0]} cy={current.anchor[1]} r={1.1} className="ax-pin-dot" />
                      </g>
                    ) : null}
                  </svg>
                  {current ? (
                    <div
                      className="ax-callout"
                      data-side={calloutSide}
                      style={{ left: `${(current.anchor[0] / width) * 100}%`, top: `${(current.anchor[1] / height) * 100}%` }}
                      aria-hidden="true"
                    >
                      <strong>{current.label}</strong>
                      <span>{current.summary}</span>
                    </div>
                  ) : null}
                </div>
              </FigureBoundary>
            </Plate>
          </div>
        </div>
        <aside className="ax-side">
          <div className="ax-live" aria-live="polite">
            {current ? `${current.label}: ${current.summary}` : ""}
          </div>
          {!compact ? (
            <ol className="ax-parts" id={`${fig}-parts`} aria-label="Components">
              {parts.map((part, i) => (
                <li key={part.id}>
                  <button className="ax-part-btn" aria-pressed={part.id === selected} onClick={() => choose(part.id === selected ? null : part.id)}>
                    <span className="ax-part-num">{String(i + 1).padStart(2, "0")}</span>
                    <span className="ax-part-label">{part.label}</span>
                    {part.status ? <span className={`ax-dot ax-dot-${part.status}`} title={part.statusLabel ?? part.status} aria-label={part.statusLabel ?? part.status} /> : null}
                  </button>
                </li>
              ))}
            </ol>
          ) : null}
          <div className="ax-detail">{detail}</div>
        </aside>
      </div>
    </section>
  );
}

export const statusLabel: Record<PartStatus, string> = {
  passed: "Passed",
  failed: "Failed",
  pending: "Pending review",
  unrun: "Not run",
  blocked: "Blocked",
  known: "Declared",
  inferred: "Inferred",
  unknown: "Unknown",
  neutral: "",
};
