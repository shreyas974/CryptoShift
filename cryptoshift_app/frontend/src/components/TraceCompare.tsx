import type { Run } from "../api/types";
import { Badge } from "./ui";

type Traces = NonNullable<Run["traces"]>;

/** Baseline vs candidate handshake events per peer, exactly as the negotiation model emitted them. */
export function TraceCompare({ traces, compact }: { traces: Traces; compact?: boolean }) {
  return (
    <div className="trace-compare">
      <p className="small muted">Source: {traces.model}</p>
      {traces.peers.map((p) => (
        <details key={p.peer} open={!compact || p.regression || p.changed}>
          <summary className="kv small">
            <strong>{p.peer}</strong>
            {p.regression ? <Badge tone="red">Regression</Badge> : p.changed ? <Badge tone="blue">Changed</Badge> : <Badge>Unchanged</Badge>}
            <span className="muted">
              {p.baseline.group ?? "—"} → {p.candidate.group ?? "—"}
            </span>
          </summary>
          <div className="grid grid-2" style={{ marginTop: 8 }}>
            {(["baseline", "candidate"] as const).map((side) => (
              <div key={side}>
                <div className="small muted" style={{ marginBottom: 4 }}>
                  {side === "baseline" ? "Baseline" : "Candidate"} · {p[side].ok ? "handshake complete" : "failed"}
                </div>
                <div className="trace">
                  {p[side].events.map((e, i) => (
                    <div key={i} className={e.step === "alert" ? "t-alert" : e.step === "finished" ? "t-finished" : ""}>
                      <span>{e.step}</span>
                      <span>{e.detail}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </details>
      ))}
    </div>
  );
}
