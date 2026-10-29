import * as React from "react";

export interface ChartSegment {
  label: string;
  value: number;
  color: string;
  sublabel?: string;
}

// ---------------- SVG Donut Chart with Hover & Tooltip ----------------
export function DonutChart({
  title,
  segments,
  size = 180,
  strokeWidth = 26,
  centerLabel,
  centerValue,
}: {
  title?: string;
  segments: ChartSegment[];
  size?: number;
  strokeWidth?: number;
  centerLabel?: string;
  centerValue?: string | number;
}) {
  const [activeIdx, setActiveIdx] = React.useState<number | null>(null);

  const total = React.useMemo(() => segments.reduce((sum, s) => sum + s.value, 0), [segments]);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  let accumulated = 0;
  const slices = segments.map((s, idx) => {
    const fraction = total > 0 ? s.value / total : 0;
    const strokeDash = fraction * circumference;
    const offset = accumulated * circumference;
    accumulated += fraction;
    return {
      ...s,
      idx,
      fraction,
      percent: Math.round(fraction * 100),
      strokeDasharray: `${strokeDash} ${circumference - strokeDash}`,
      strokeDashoffset: -offset,
    };
  });

  const activeSegment = activeIdx !== null ? slices[activeIdx] : null;

  return (
    <div className="donut-chart-wrap" style={{ display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap" }}>
      <div style={{ position: "relative", width: size, height: size, flex: "none" }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: "rotate(-90deg)" }} role="img" aria-label={title ?? "Distribution chart"}>
          {/* Background track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="rgba(0, 0, 0, 0.05)"
            strokeWidth={strokeWidth}
          />
          {slices.map((s) => {
            const isHovered = activeIdx === s.idx;
            return (
              <circle
                key={s.label}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={s.color}
                strokeWidth={isHovered ? strokeWidth + 4 : strokeWidth}
                strokeDasharray={s.strokeDasharray}
                strokeDashoffset={s.strokeDashoffset}
                style={{
                  cursor: "pointer",
                  transition: "stroke-width 0.2s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease",
                  opacity: activeIdx === null || isHovered ? 1 : 0.65,
                }}
                onMouseEnter={() => setActiveIdx(s.idx)}
                onMouseLeave={() => setActiveIdx(null)}
              />
            );
          })}
        </svg>

        {/* Center label */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            pointerEvents: "none",
            textAlign: "center",
            padding: 8,
          }}
        >
          <span style={{ fontSize: 20, fontWeight: 800, color: "var(--cs-text)", fontVariantNumeric: "tabular-nums" }}>
            {activeSegment ? activeSegment.value : (centerValue ?? total)}
          </span>
          <span style={{ fontSize: 11, color: "var(--cs-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em", maxWidth: 90, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {activeSegment ? activeSegment.label : (centerLabel ?? "Total")}
          </span>
        </div>
      </div>

      {/* Legend list */}
      <div style={{ flex: "1 1 160px", display: "grid", gap: 7 }}>
        {title ? <div style={{ fontSize: 13, fontWeight: 700, color: "var(--cs-text)", marginBottom: 2 }}>{title}</div> : null}
        {slices.map((s) => {
          const isHovered = activeIdx === s.idx;
          return (
            <div
              key={s.label}
              onMouseEnter={() => setActiveIdx(s.idx)}
              onMouseLeave={() => setActiveIdx(null)}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 8,
                fontSize: 12.5,
                padding: "3px 6px",
                borderRadius: 6,
                cursor: "pointer",
                background: isHovered ? "rgba(254, 243, 199, 0.5)" : "transparent",
                transition: "background 0.15s ease",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                <span style={{ width: 10, height: 10, borderRadius: "50%", background: s.color, flex: "none" }} />
                <span style={{ color: "var(--cs-text)", fontWeight: isHovered ? 700 : 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {s.label}
                </span>
              </div>
              <div style={{ display: "flex", gap: 6, alignItems: "center", flex: "none" }}>
                <strong style={{ fontVariantNumeric: "tabular-nums", color: "var(--cs-text)" }}>{s.value}</strong>
                <span className="muted" style={{ fontSize: 11 }}>({s.percent}%)</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------- Visual Horizontal Bar Chart ----------------
export function BarChart({
  items,
  max,
}: {
  items: { label: string; count: number; color: string; sub?: string }[];
  max?: number;
}) {
  const peak = max ?? Math.max(...items.map((i) => i.count), 1);

  return (
    <div style={{ display: "grid", gap: 10, width: "100%" }}>
      {items.map((item) => {
        const pct = Math.round((item.count / peak) * 100);
        return (
          <div key={item.label} style={{ display: "grid", gap: 4 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
              <span style={{ fontWeight: 600, color: "var(--cs-text)" }}>{item.label}</span>
              <span style={{ color: "var(--cs-muted)", fontVariantNumeric: "tabular-nums" }}>
                <strong>{item.count}</strong> {item.sub ? `· ${item.sub}` : ""}
              </span>
            </div>
            <div style={{ width: "100%", height: 8, borderRadius: 9999, background: "rgba(0,0,0,0.06)", overflow: "hidden" }}>
              <div
                style={{
                  width: `${pct}%`,
                  height: "100%",
                  background: item.color,
                  borderRadius: 9999,
                  transition: "width 0.6s cubic-bezier(0.16, 1, 0.3, 1)",
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------- Wave Timeline Visualizer ----------------
export function WaveVisualizer({
  waves,
  cycles,
}: {
  waves: string[][];
  cycles: { members: string[] }[];
}) {
  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${waves.length + (cycles.length ? 1 : 0)}, minmax(0, 1fr))`, gap: 12 }}>
        {waves.map((wave, idx) => (
          <div
            key={idx}
            style={{
              background: "var(--cs-surface-glass-card)",
              border: "1.5px solid var(--cs-border)",
              borderTop: "3px solid var(--cs-blue)",
              borderRadius: 12,
              padding: "12px 14px",
              boxShadow: "var(--cs-shadow)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: "var(--cs-blue)" }}>Wave {idx + 1}</span>
              <span className="badge badge-blue">{wave.length} services</span>
            </div>
            <ul className="list small" style={{ gap: 6 }}>
              {wave.map((service) => (
                <li key={service} style={{ background: "rgba(37, 99, 235, 0.06)", padding: "4px 8px", borderRadius: 6, fontSize: 12, fontWeight: 600 }}>
                  {service}
                </li>
              ))}
            </ul>
          </div>
        ))}

        {cycles.length > 0 ? (
          <div
            style={{
              background: "var(--cs-red-bg)",
              border: "1.5px solid rgba(225, 29, 72, 0.3)",
              borderTop: "3px solid var(--cs-red)",
              borderRadius: 12,
              padding: "12px 14px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: "var(--cs-red)" }}>Blocked (Cycle)</span>
              <span className="badge badge-red">{cycles.length} deadlock</span>
            </div>
            <p style={{ fontSize: 12, color: "#9f1239", lineHeight: 1.45 }}>
              Circular dependency prevents automatic wave scheduling:
            </p>
            <ul className="list small" style={{ marginTop: 6, gap: 4 }}>
              {cycles.map((c, i) => (
                <li key={i} className="mono" style={{ fontSize: 11, color: "var(--cs-red)" }}>
                  {c.members.join(" ↔ ")}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  );
}

