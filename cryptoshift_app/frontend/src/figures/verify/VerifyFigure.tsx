import * as React from "react";
import { AnatomyFrame, type PartInfo } from "../../anatomy/AnatomyFrame";
import { useLoop, follow } from "../../anatomy/kit/react/live";
import { LineBench, Stations, Rail, Carriage, BarrierArm, W, H, anchorOf, carriageX } from "./VerifyArt";
import { stationsOf, stopOf, type StationId } from "./model";
import type { Checkpoint, Patch, Run } from "../../api/types";
import { CheckBadge, Diff, Field, VerdictBadge, Badge, mono } from "../../components/ui";
import { ReviewActions } from "../../components/ReviewActions";
import { TraceCompare } from "../../components/TraceCompare";

export function VerifyFigure({ patch, run, checkpoint, toolbar }: { patch: Patch; run: Run | null; checkpoint: Checkpoint | null; toolbar?: React.ReactNode }) {
  const stations = React.useMemo(() => stationsOf(patch, run, checkpoint), [patch, run, checkpoint]);
  const stop = stopOf(stations);
  const goal = carriageX(stop);
  const [x, setX] = React.useState(goal);
  const shown = React.useRef(goal);
  const kick = useLoop((dt, calm) => {
    shown.current = follow(shown.current, goal, dt, 0.45, calm);
    setX(shown.current);
    return shown.current !== goal;
  }, false);
  React.useEffect(() => kick(), [goal, kick]);

  const firstBad = stations.find((s) => s.status === "failed" || s.status === "blocked");
  const [selected, setSelected] = React.useState<string | null>(firstBad?.id ?? "candidate");
  const carriageStatus = firstBad && stop < 8 ? "failed" : stop >= 8 ? "passed" : "pending";

  const parts: PartInfo[] = stations.map((s) => ({
    id: s.id,
    label: s.label,
    summary: s.summary,
    readout: s.readout,
    status: s.status,
    statusLabel: s.statusLabel,
    anchor: anchorOf(s.id, x),
    related: s.id === "candidate" ? [] : s.id === "report" ? ["diff", "build", "tests", "vectors", "protocol"] : undefined,
  }));
  const sel = stations.find((s) => s.id === selected) ?? null;
  const releaseRaised = stations.find((s) => s.id === "release")!.status === "passed";
  const verdictText = !run ? "not verified" : run.status === "running" ? "verification running" : run.verdict === "verified_candidate" ? "verified candidate" : run.verdict ?? "—";

  return (
    <AnatomyFrame
      fig="Fig 04"
      title="Verified migration"
      ariaLabel={`Inspection line for the patch to ${patch.file} line ${patch.line}; the carriage stops at the first station it cannot clear`}
      width={W}
      height={H}
      parts={parts}
      selected={selected}
      onSelect={setSelected}
      idleReadout={verdictText}
      hint="Select a station"
      keys={[
        { mark: "lit", label: "Candidate patch on its carriage" },
        { mark: "raised", label: "Check station (lamp = real result)" },
        { mark: "red", label: "Release barrier closed" },
      ]}
      caption={
        <span>
          The carriage position is computed from the latest run: it rests at the first station that has not passed. Lamps: green passed, red failed or blocked, amber pending or awaiting a human, white not run. "Verified candidate" means every configured required check passed — it is not a proof of absolute security.
        </span>
      }
      toolbar={toolbar}
      detail={sel ? <StationDetail id={sel.id} patch={patch} run={run} checkpoint={checkpoint} stations={stations} /> : <p className="muted">Select a station to see its real check result, or the carriage for review actions.</p>}
    >
      <LineBench />
      <Stations stations={stations} />
      <Rail />
      <g className="ax-part" data-part="candidate">
        <Carriage x={x} status={carriageStatus} />
      </g>
      <g className="ax-part" data-part="release">
        <BarrierArm raised={releaseRaised} />
      </g>
    </AnatomyFrame>
  );
}

function StationDetail({ id, patch, run, checkpoint, stations }: { id: StationId; patch: Patch; run: Run | null; checkpoint: Checkpoint | null; stations: ReturnType<typeof stationsOf> }) {
  const s = stations.find((x) => x.id === id)!;
  const c = s.check;
  const header = (
    <div className="kv" style={{ justifyContent: "space-between" }}>
      <h3>{s.label}</h3>
      {c ? <CheckBadge status={c.status} /> : <Badge tone={s.status === "passed" ? "green" : s.status === "failed" || s.status === "blocked" ? "red" : s.status === "pending" ? "amber" : "grey"}>{s.statusLabel}</Badge>}
    </div>
  );
  const runCheck = run?.checks.find((x) => x.id === id);
  switch (id) {
    case "legacy":
      return (
        <>
          {header}
          <p>{s.summary}</p>
          <pre className="code"><div className="code-line"><span className="code-num">{patch.line}</span><code>{patch.before}</code></div></pre>
        </>
      );
    case "candidate":
      return (
        <>
          {header}
          <dl className="fields">
            <Field label="Proposer">{patch.proposer}</Field>
            <Field label="Introduces">{patch.algorithms.join(", ") || "—"}</Field>
            <Field label="Patch hash">{mono(patch.hash.slice(0, 16))}</Field>
          </dl>
          <p className="small">{patch.rationale}</p>
          <ReviewActions patch={patch} checkpointId={checkpoint?.status === "active" ? checkpoint.id : null} />
        </>
      );
    case "report":
      return (
        <>
          <div className="kv" style={{ justifyContent: "space-between" }}>
            <h3>Verification report</h3>
            <VerdictBadge verdict={run ? (run.status === "running" ? "running" : run.verdict) : "not_run"} />
          </div>
          <p className="small">{s.summary}</p>
          {run ? (
            <ul className="list small">
              {run.checks.map((x) => (
                <li key={x.id} style={{ justifyContent: "space-between" }}>
                  <span>
                    {x.name}
                    {x.required ? "" : " (not required)"}
                  </span>
                  <CheckBadge status={x.status} />
                </li>
              ))}
            </ul>
          ) : null}
          {run?.verdict === "failed" ? <p className="note">A failed required check returns the patch to revision. It cannot be approved; propose a revised patch or reject it.</p> : null}
        </>
      );
    case "approval":
    case "release":
    case "rollback":
      return (
        <>
          {header}
          <p className="small">{s.summary}</p>
          {patch.decisions.length ? (
            <ul className="list small">
              {patch.decisions.map((d, i) => (
                <li key={i}>
                  <Badge>{d.decision}</Badge> {d.reviewer} · {new Date(d.at).toLocaleString()} {d.note ? `— ${d.note}` : ""}
                </li>
              ))}
            </ul>
          ) : null}
          {checkpoint && id === "rollback" ? (
            <dl className="fields">
              <Field label="Original">{mono(checkpoint.originalHash.slice(0, 16))}</Field>
              <Field label="Released">{mono(checkpoint.releasedHash.slice(0, 16))}</Field>
            </dl>
          ) : null}
          <ReviewActions patch={patch} checkpointId={checkpoint?.status === "active" ? checkpoint.id : null} />
        </>
      );
    default:
      return (
        <>
          {header}
          <p className="small">{runCheck?.detail || s.summary}</p>
          {runCheck?.note ? <p className="note">{runCheck.note}</p> : null}
          {id === "diff" ? <Diff diff={patch.diff} /> : null}
          {id === "tests" && runCheck?.candidate ? (
            <dl className="fields">
              <Field label="Baseline">{runCheck.baseline!.ran - runCheck.baseline!.failing.length}/{runCheck.baseline!.ran} passed</Field>
              <Field label="Candidate">{runCheck.candidate.ran - runCheck.candidate.failing.length}/{runCheck.candidate.ran} passed</Field>
              {runCheck.regressions?.length ? <Field label="Regressions">{runCheck.regressions.map((r) => <div key={r}>{mono(r)}</div>)}</Field> : null}
              {runCheck.candidate.reasons.length ? <Field label="Reason">{runCheck.candidate.reasons.join("; ")}</Field> : null}
            </dl>
          ) : null}
          {id === "vectors" && runCheck?.results ? (
            <ul className="list small">
              {runCheck.results.map((r) => (
                <li key={r.algorithm}>
                  <Badge tone={r.status === "passed" ? "green" : r.status === "failed" ? "red" : "grey"}>{r.algorithm}</Badge> {r.detail}
                </li>
              ))}
            </ul>
          ) : null}
          {id === "protocol" && run?.traces ? <TraceCompare traces={run.traces} compact /> : null}
          {!run ? <p className="note">No verification run exists for this patch. Nothing here is assumed to pass.</p> : null}
          {runCheck?.output && id !== "diff" ? (
            <details>
              <summary className="small">Raw output</summary>
              <pre className="code" style={{ maxHeight: 220, padding: "8px 12px" }}>{runCheck.output}</pre>
            </details>
          ) : null}
        </>
      );
  }
}
