import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useState } from "react";
import { api, type ApprovalStep, type FindingRow, type Me } from "../api/client";
import { DataTable } from "../components/DataTable";
import { HeroSphere } from "../components/HeroSphere";
import { PipelineFigure } from "../components/PipelineFigure";
import { ActivityList } from "./tier3";
import type { Prefs } from "../lib/prefs";
import {
  Badge,
  BarList,
  Card,
  ErrorState,
  Evidence,
  Kpi,
  Loading,
  Notice,
  ScannedText,
  SourceFooter,
  StatusCard,
} from "../components/ui";
import { canApprove, normStatus, plainText } from "../lib/status";

/* eslint-disable @typescript-eslint/no-explicit-any */

export function OverviewPage({ me, go, prefs }: { me: Me; go: (p: string) => void; prefs: Prefs }) {
  const q = useQuery({ queryKey: ["overview"], queryFn: api.overview });
  const plan = useQuery({ queryKey: ["plan"], queryFn: api.plan });
  const appr = useQuery({ queryKey: ["approvals"], queryFn: api.approvals });
  if (q.isLoading) return <Loading what="overview" />;
  if (q.error || !q.data) return <ErrorState error={q.error} />;
  const o = q.data;
  const src = o.sources["plan"];
  const nodes = (appr.data?.steps ?? []).map((s) => ({ id: s.service, state: s.approved ? "APPROVED" : s.state }));
  const ready = o.counts.steps_ready ?? 0;
  const total = o.counts.steps_total ?? 0;
  return (
    <>
      <section className="hero" aria-labelledby="hero-title">
        <div>
          <div className="eyebrow">PQC-01 · Post-quantum migration console</div>
          <h1 id="hero-title" className="display">
            Find, plan and verify your <span className="grad-text">post-quantum</span> migration.
          </h1>
          <p className="lede">
            CryptoShift inventories the cryptography in your systems, orders the migration by dependency and risk, and
            checks each step against loopback evidence before a human approves it.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <a href="#/runs" className="btn btn-primary no-underline">
              Analyse your dataset
            </a>
            <a href="#/plan" className="btn no-underline">
              Open the migration plan
            </a>
          </div>
          <div className="mt-8">
            <a href="#overview-status" className="scroll-cue">
              <span aria-hidden="true">↓</span> Current status
            </a>
          </div>
        </div>
        <HeroSphere theme={prefs.theme} reduceMotion={prefs.reduceMotion} nodes={nodes} />
      </section>
      <section className="section" aria-labelledby="pillars">
        <div className="eyebrow">How it works</div>
        <h2 id="pillars" className="h-section mb-6">
          Three steps, each with its evidence
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {(
            [
              [
                "01",
                "Discover",
                `${o.counts.findings ?? "–"}`,
                "findings",
                "Scan configs and code for RSA, ECC, 3DES and friends, with purpose and confidence. Unknown purpose is held.",
                "inventory",
                "Explore the inventory",
              ],
              [
                "02",
                "Plan",
                `${o.counts.services ?? "–"}`,
                "services",
                "Build the dependency graph and a deterministic wave schedule; compare it with QpiAI Opt and a simulator QAOA run.",
                "plan",
                "See the plan",
              ],
              [
                "03",
                "Verify",
                `${ready}/${total}`,
                "steps READY",
                "Run loopback handshakes, compatibility and rollback gates; only READY steps can be approved by a person.",
                "verification",
                "Check the gates",
              ],
            ] as const
          ).map(([n, t, stat, unit, body, to, cta]) => (
            <article key={t} className="glass glass-card lift glow-border feature-card">
              <span className="fc-num">{n}</span>
              <h3 className="m-0 text-xl font-semibold">{t}</h3>
              <div>
                <span className="fc-stat">{stat}</span> <span className="t-muted text-sm">{unit}</span>
              </div>
              <p className="t-muted m-0 text-sm">{body}</p>
              <div className="fc-foot">
                <a href={`#/${to}`} className="arrow-link">
                  {cta}
                </a>
              </div>
            </article>
          ))}
        </div>
      </section>
      <div id="overview-status" className="section" />
      <StatusCard status={src?.status ?? "missing"} source={src} />
      <Card title="Pipeline" className="mb-4">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {o.stages.map((s) => (
            <div key={s.name} className="glass rounded-xl p-3">
              <div className="t-muted text-xs font-semibold tracking-widest uppercase">{s.name}</div>
              <div className="my-2">
                <Badge value={s.status} />
              </div>
              <div className="t-muted text-sm">
                <Evidence source={o.sources[s.source]} label={s.name}>
                  {s.note}
                </Evidence>
              </div>
            </div>
          ))}
        </div>
      </Card>
      {plan.data?.tasks && appr.data && (
        <div className="mb-4">
          <PipelineFigure
            services={(plan.data.tasks as { service: string; wave: number | null }[])
              .filter((t) => t.wave !== null)
              .map((t) => {
                const st = appr.data.steps.find((x) => x.service === t.service);
                return {
                  id: t.service,
                  wave: t.wave ?? 0,
                  state: st?.approved ? "APPROVED" : (st?.state ?? "unknown"),
                };
              })}
            findings={o.counts.findings ?? 0}
            objective={(plan.data.objective as number | null) ?? null}
            readyCount={o.counts.steps_ready ?? 0}
            approvedCount={appr.data.approved_steps.length}
            theme={prefs.theme}
            reduceMotion={prefs.reduceMotion}
          />
        </div>
      )}
      <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Kpi
          label="Findings"
          value={o.counts.findings ?? "–"}
          note={`${o.counts.services ?? "–"} services`}
          source={src}
        />
        <Kpi
          label="Steps READY"
          value={`${o.counts.steps_ready ?? "–"} / ${o.counts.steps_total ?? "–"}`}
          note="generic loopback evidence"
          source={src}
        />
        <Kpi
          label="Held-out recall"
          value={o.counts.held_out_recall ?? "–"}
          note="P 1.0 · AI-draft labels"
          source={o.sources["eval_held_out"]}
        />
        <Kpi
          label="Plan hash"
          value={<span className="text-xl">{o.plan_hash?.slice(0, 12) ?? "–"}</span>}
          note="changes invalidate approvals"
          source={src}
        />
      </div>
      <Notice tone="info">
        READY means the generic loopback evidence passed and the purpose is resolved. It is not verification of the
        service's own production stack.
      </Notice>
      {me.role !== "viewer" && <JobsCard />}
      <section className="section" aria-labelledby="latest">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <div className="eyebrow">Latest</div>
            <h2 id="latest" className="h-section">
              Activity
            </h2>
          </div>
          <span className="flex-1" />
          <a href="#/activity" className="arrow-link mb-2">
            View all activity
          </a>
        </div>
        <LatestActivity />
      </section>
      <section className="band section mt-10" aria-labelledby="byod">
        <div className="grid grid-cols-1 items-center gap-6 md:grid-cols-[1fr_auto]">
          <div>
            <div className="eyebrow">Bring your own dataset</div>
            <h2 id="byod" className="h-section">
              Run the pipeline on your own configs and code
            </h2>
            <p className="t-muted m-0 max-w-2xl">
              Upload a folder or a .zip. Get findings, a CBOM-like inventory, CycloneDX, the dependency graph and a
              migration plan, all computed on this machine.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn btn-primary" onClick={() => go("runs")}>
              Start a run
            </button>
            <button type="button" className="btn" onClick={() => go("reports")}>
              Get the report
            </button>
          </div>
        </div>
      </section>
      <SourceFooter sources={[src, o.sources["scheduling"]]} />
    </>
  );
}

function LatestActivity() {
  const q = useQuery({ queryKey: ["activity", 6], queryFn: () => api.activity(6), refetchInterval: 30_000 });
  if (q.isLoading) return <Loading what="activity" />;
  if (q.error || !q.data) return <ErrorState error={q.error} />;
  return <ActivityList items={q.data.items} />;
}

function JobsCard() {
  const qc = useQueryClient();
  const cmds = useQuery({ queryKey: ["commands"], queryFn: api.commands });
  const [jobId, setJobId] = useState<number | null>(null);
  const [err, setErr] = useState("");
  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.job(jobId ?? 0),
    enabled: jobId !== null,
    refetchInterval: (query) =>
      ["queued", "running"].includes((query.state.data as any)?.status ?? "queued") ? 1000 : false,
  });
  const status = (job.data as any)?.status as string | undefined;
  if (status && !["queued", "running"].includes(status))
    void qc.invalidateQueries({ predicate: (qq) => qq.queryKey[0] !== "job" });
  return (
    <Card title="Run and reload (allow-listed commands)" className="mb-4">
      <div className="flex flex-wrap gap-2">
        {(cmds.data ?? []).map((c) => (
          <button
            key={c.id}
            type="button"
            className="btn"
            disabled={status === "running" || status === "queued"}
            onClick={async () => {
              setErr("");
              try {
                setJobId((await api.startJob(c.id)).job_id);
              } catch (e) {
                setErr(e instanceof Error ? e.message : "failed");
              }
            }}
          >
            {c.label}
          </button>
        ))}
      </div>
      {err && <p className="t-bad text-sm">{plainText(err, 300)}</p>}
      {job.data && (
        <div className="mt-3 text-sm" aria-live="polite">
          Job #{jobId}:{" "}
          <Badge
            value={status === "succeeded" ? "PASS" : status === "failed" || status === "timeout" ? "FAIL" : "PROPOSED"}
          />{" "}
          {status}
          {(job.data as any).output_tail && (
            <pre
              className="mono mt-2 max-h-48 overflow-auto text-xs whitespace-pre-wrap"
              tabIndex={0}
              aria-label="Job output"
            >
              {plainText((job.data as any).output_tail, 4000)}
            </pre>
          )}
        </div>
      )}
    </Card>
  );
}

export function InventoryPage() {
  const q = useQuery({ queryKey: ["findings"], queryFn: api.findings });
  const [hold, setHold] = useState(false);
  const [sel, setSel] = useState<FindingRow | null>(null);
  if (q.isLoading) return <Loading what="findings" />;
  if (q.error || !q.data) return <ErrorState error={q.error} />;
  const d = q.data;
  const rows = hold ? d.rows.filter((r) => r.hold) : d.rows;
  const cols: ColumnDef<FindingRow, unknown>[] = [
    { header: "ID", accessorKey: "id", cell: (c) => <span className="mono">{String(c.getValue())}</span> },
    {
      header: "Location",
      accessorFn: (r) => `${r.file}:${r.line}`,
      cell: (c) => <code className="text-xs">{plainText(c.getValue(), 120)}</code>,
    },
    { header: "Service", accessorKey: "service" },
    { header: "Family", accessorKey: "family" },
    {
      header: "Purpose",
      accessorKey: "purpose",
      cell: (c) => (c.getValue() === "unknown" ? <Badge value="HOLD" /> : String(c.getValue())),
    },
    { header: "Confidence", accessorKey: "confidence" },
    {
      header: "Candidate (human review)",
      accessorKey: "candidate",
      cell: (c) => <span className="text-xs">{plainText(c.getValue(), 200)}</span>,
    },
  ];
  const byPurpose = Object.entries(
    rows.reduce<Record<string, number>>((a, r) => ((a[r.purpose] = (a[r.purpose] ?? 0) + 1), a), {}),
  ).map(([label, value]) => ({ label, value }));
  return (
    <>
      <StatusCard status={d.status} source={d.source} />
      <Notice>
        {d.notice} ML-KEM (FIPS 203) is key establishment only; ML-DSA (FIPS 204) and SLH-DSA (FIPS 205) are signatures
        only.
      </Notice>
      <Card
        title={
          <Evidence source={d.source} label="findings">
            Findings
          </Evidence>
        }
        actions={
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={hold} onChange={(e) => setHold(e.target.checked)} /> Only HOLD (unknown
            purpose)
          </label>
        }
        className="mb-4"
      >
        <DataTable data={rows} columns={cols} caption="Findings" onRowClick={setSel} />
      </Card>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="By purpose">
          <BarList title="Findings by purpose (current filter)" rows={byPurpose} />
        </Card>
        <Card title="Selected finding">
          {sel ? (
            <dl className="m-0 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
              <dt className="t-muted">ID</dt>
              <dd className="m-0 mono">{sel.id}</dd>
              <dt className="t-muted">Location</dt>
              <dd className="m-0">
                <ScannedText value={`${sel.file}:${sel.line}`} limit={300} />
              </dd>
              <dt className="t-muted">Snippet (redacted)</dt>
              <dd className="m-0">
                <ScannedText value={sel.snippet} />
              </dd>
              <dt className="t-muted">Rationale</dt>
              <dd className="m-0">{plainText(sel.rationale, 500)}</dd>
              <dt className="t-muted">Service basis</dt>
              <dd className="m-0">
                {plainText(sel.service_basis, 300)} ({sel.service_confidence})
              </dd>
              <dt className="t-muted">Detector</dt>
              <dd className="m-0">{sel.detector}</dd>
            </dl>
          ) : (
            <p className="t-muted">Select a row (click or Enter) to see its evidence.</p>
          )}
        </Card>
      </div>
      <SourceFooter sources={[d.source]} />
    </>
  );
}

export function PlanPage() {
  const q = useQuery({ queryKey: ["plan"], queryFn: api.plan });
  if (q.isLoading) return <Loading what="migration plan" />;
  if (q.error) return <ErrorState error={q.error} />;
  const p = q.data as any;
  const waves = Object.keys(p.waves ?? {}).sort();
  const c = p.comparison;
  return (
    <>
      <StatusCard status={p.status} source={p.source} />
      <Notice>
        Risk score: provisional, not validated. Scheduling numbers are assumptions (docs/member3/assumptions.md).
      </Notice>
      <Card
        title={`Wave timeline (objective ${p.objective}, dependency violations ${p.dependency_violations})`}
        className="mb-4"
      >
        <div className="flex flex-col gap-2" role="list" aria-label="Waves">
          {waves.map((w) => (
            <div key={w} role="listitem" className="grid grid-cols-[90px_1fr] items-center gap-3">
              <span className="mono t-muted">Wave {w}</span>
              <div className="flex flex-wrap gap-2">
                {(p.waves[w] as string[]).map((s) => (
                  <span key={s} className="glass rounded-lg px-3 py-1 text-sm">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>
      <Card title="Tasks" className="mb-4">
        <table className="dtable">
          <thead>
            <tr>
              {["Service", "Wave", "Risk (provisional)", "Evidence", "Findings", "Reason"].map((h) => (
                <th key={h} scope="col">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(p.tasks as any[]).map((t) => (
              <tr key={t.service}>
                <td>{t.service}</td>
                <td className="num">{t.wave ?? "–"}</td>
                <td className="num">{t.risk}</td>
                <td>
                  <Badge value={t.evidence_source === "OBSERVED" ? "OBSERVED" : "DECLARED"} />
                </td>
                <td className="mono text-xs">{(t.finding_ids as string[]).join(", ") || "–"}</td>
                <td className="text-xs">{plainText(t.risk_reason, 300)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      {c && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card title="Deterministic baseline">
            <Badge value={c.baseline.status} />
            <div className="mono mt-2 text-3xl">
              <Evidence source={p.scheduling_source} label="baseline objective">
                {c.baseline.objective}
              </Evidence>
            </div>
            <p className="t-muted text-sm">exact search · {c.baseline.runtime_s} s · lower is better</p>
          </Card>
          <Card title="QpiAI Opt local solve">
            <Badge value={c.qpiai_opt.status} />
            <div className="mono mt-2 text-3xl">{c.qpiai_opt.objective ?? "–"}</div>
            <p className="t-muted text-sm">
              {c.qpiai_opt.solver_status ?? plainText(c.qpiai_opt.reason, 200)} · <strong>{c.qpiai_opt.verdict}</strong>
            </p>
          </Card>
          <Card title="QCloud QAOA (Wave 0)">
            <Badge value="SIMULATOR" />
            <div className="mono mt-2 text-3xl">P {c.qcloud_qaoa.optimum_probability}</div>
            <p className="t-muted text-sm">
              vs uniform {c.qcloud_qaoa.uniform_probability} · {c.qcloud_qaoa.verdict}
            </p>
          </Card>
        </div>
      )}
      <SourceFooter sources={[p.source, p.scheduling_source]} />
    </>
  );
}

export function VerificationPage() {
  const q = useQuery({ queryKey: ["verification"], queryFn: api.verification });
  if (q.isLoading) return <Loading what="verification" />;
  if (q.error) return <ErrorState error={q.error} />;
  const v = q.data as any;
  const gates: string[] = [...new Set<string>((v.steps as any[]).flatMap((s) => s.gates.map((g: any) => g.gate)))];
  const traces = Object.entries(v.traces ?? {}) as [string, any][];
  return (
    <>
      <StatusCard status={v.status} source={v.source} />
      <Notice tone="info">{v.label}. Loopback timing is not network timing.</Notice>
      <Card title="Gate matrix" className="mb-4">
        <div className="overflow-auto" tabIndex={0} role="region" aria-label="Scrollable table">
          <table className="dtable">
            <thead>
              <tr>
                <th scope="col">Step</th>
                <th scope="col">State</th>
                {gates.map((g) => (
                  <th key={g} scope="col">
                    {g}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(v.steps as any[]).map((s) => (
                <tr key={s.step_id}>
                  <td className="mono text-xs">{s.step_id}</td>
                  <td>
                    <Badge value={s.state} />
                  </td>
                  {gates.map((g) => {
                    const gg = s.gates.find((x: any) => x.gate === g);
                    return (
                      <td key={g} title={gg ? plainText(gg.reason, 200) : ""}>
                        <Badge value={gg?.status ?? "UNKNOWN"} />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <Card title="Compatibility matrix (negative cases must be rejected)" className="mb-4">
        <div className="overflow-auto" tabIndex={0} role="region" aria-label="Scrollable table">
          <table className="dtable">
            <thead>
              <tr>
                {["Case", "Type", "Expected", "Observed", "Result"].map((h) => (
                  <th key={h} scope="col">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(v.compatibility as any[]).map((r) => (
                <tr key={r.case}>
                  <td>{r.case}</td>
                  <td>{r.category}</td>
                  <td className="text-xs">{r.expected}</td>
                  <td className="text-xs">{r.observed}</td>
                  <td>
                    <Badge value={r.pass ? "PASS" : "FAIL"} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        {traces.map(([k, t]) => (
          <Card key={k} title={k.replaceAll("_", " ")}>
            <Badge value="VERIFIED" title="TEST SCENARIO, loopback" />
            <dl className="m-0 mt-2 grid grid-cols-[auto_1fr] gap-x-3 text-sm">
              {(["protocol", "group", "cipher", "bytes_read", "bytes_written", "peer_signature_type"] as const).map(
                (f) => (
                  <div key={f} className="contents">
                    <dt className="t-muted">{f.replaceAll("_", " ")}</dt>
                    <dd className="mono m-0">{String(t[f] ?? "–")}</dd>
                  </div>
                ),
              )}
            </dl>
          </Card>
        ))}
      </div>
      {v.overhead && (
        <Card title="Overhead (TEST SCENARIO; process start-up dominates)">
          <p className="t-muted text-sm">{plainText(v.overhead.method, 400)}</p>
          <table className="dtable">
            <thead>
              <tr>
                <th scope="col">Config</th>
                {Object.keys(Object.values(v.overhead.results)[0] as object)
                  .filter((k) => typeof (Object.values(v.overhead.results)[0] as any)[k] !== "object")
                  .map((k) => (
                    <th key={k} scope="col">
                      {k}
                    </th>
                  ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(v.overhead.results as Record<string, any>).map(([cfg, r]) => (
                <tr key={cfg}>
                  <td>{cfg}</td>
                  {Object.entries(r)
                    .filter(([, val]) => typeof val !== "object")
                    .map(([k, val]) => (
                      <td key={k} className="num">
                        {String(val)}
                      </td>
                    ))}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="t-muted mt-2 text-xs">
            Environment:{" "}
            {Object.entries(v.overhead.environment ?? {})
              .map(([k, val]) => `${k}=${plainText(val, 80)}`)
              .join(" · ")}
          </p>
        </Card>
      )}
      <SourceFooter sources={[v.source, v.plan_source]} />
    </>
  );
}

export function ApprovalPage({ me }: { me: Me }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["approvals"], queryFn: api.approvals });
  const rb = useQuery({ queryKey: ["rollback"], queryFn: api.rollback });
  const [step, setStep] = useState<ApprovalStep | undefined>();
  if (q.isLoading) return <Loading what="approvals" />;
  if (q.error || !q.data) return <ErrorState error={q.error} />;
  const a = q.data;
  return (
    <>
      <StatusCard status={a.status} source={a.source} />
      <Notice>
        Only a human with the approver role approves, one READY step at a time. The assistant and the UI cannot approve
        on their own; there is no "approve all".
      </Notice>
      <Card title={`Steps (plan hash ${a.plan_hash?.slice(0, 12) ?? "–"}…)`} className="mb-4">
        <table className="dtable">
          <thead>
            <tr>
              {["Step", "State", "Blocked by", "Approved", ""].map((h) => (
                <th key={h} scope="col">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {a.steps.map((s) => (
              <tr key={s.step_id}>
                <td className="mono text-xs">{s.step_id}</td>
                <td>
                  <Badge value={s.approved ? "APPROVED" : s.state} />
                </td>
                <td className="text-xs">{s.blocking.join(", ") || "–"}</td>
                <td>{s.approved ? "yes" : "no"}</td>
                <td>
                  <button
                    type="button"
                    className="btn"
                    disabled={me.role !== "approver"}
                    onClick={() => setStep(s)}
                    title={me.role !== "approver" ? "requires the approver role" : undefined}
                  >
                    Review…
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {a.invalidated.length > 0 && (
          <p className="t-warn text-sm">
            {a.invalidated.length} earlier approval(s) INVALIDATED because the plan changed.
          </p>
        )}
      </Card>
      <ApprovalDialog
        step={step}
        planHash={a.plan_hash}
        onClose={() => setStep(undefined)}
        onDone={() => {
          setStep(undefined);
          void qc.invalidateQueries();
        }}
      />
      {rb.data && (
        <Card title="Rollback plan (rehearsed on a copy)">
          <dl className="m-0 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
            {(["restore", "trigger", "recovery_check", "snapshot_sha256"] as const).map((k) => (
              <div key={k} className="contents">
                <dt className="t-muted">{k.replaceAll("_", " ")}</dt>
                <dd className="m-0 break-all">{plainText((rb.data as any).rollback?.[k], 300)}</dd>
              </div>
            ))}
            {Object.entries((rb.data as any).rollback?.rehearsal_result ?? {}).map(([k, val]) => (
              <div key={k} className="contents">
                <dt className="t-muted">rehearsal: {k.replaceAll("_", " ")}</dt>
                <dd className="m-0">
                  {typeof val === "boolean" ? <Badge value={val ? "PASS" : "FAIL"} /> : plainText(val, 200)}
                </dd>
              </div>
            ))}
          </dl>
          <Notice tone="bad">{(rb.data as any).warning}</Notice>
        </Card>
      )}
      <SourceFooter sources={[a.source]} />
    </>
  );
}

export function ApprovalDialog({
  step,
  planHash,
  onClose,
  onDone,
}: {
  step: ApprovalStep | undefined;
  planHash: string | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const [name, setName] = useState("");
  const [hash, setHash] = useState("");
  const [ack, setAck] = useState(false);
  const check = canApprove(step, name, hash, planHash, ack);
  const m = useMutation({
    mutationFn: () => {
      if (!step) throw new Error("no step selected");
      return api.approve(step.step_id, name.trim(), hash.trim().toLowerCase());
    },
    onSuccess: onDone,
  });
  return (
    <Dialog.Root open={!!step} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40" />
        <Dialog.Content
          className="glass glass-overlay fixed top-1/2 left-1/2 z-50 w-[min(520px,92vw)] -translate-x-1/2 -translate-y-1/2 p-5"
          aria-describedby="approve-desc"
        >
          <Dialog.Title className="mt-0 text-xl font-semibold">Approve {step?.step_id}</Dialog.Title>
          <p id="approve-desc" className="t-muted text-sm">
            State <Badge value={step?.state} /> · all required gates pass:{" "}
            {step?.all_required_gates_pass ? "yes" : "no"}. This records your name, the time and the plan hash. Any
            later plan change invalidates it.
          </p>
          <label className="mt-3 block text-sm">
            Approver name
            <input className="input mt-1 block w-full" value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="mt-3 block text-sm">
            Plan hash (first 12+ characters)
            <input className="input mono mt-1 block w-full" value={hash} onChange={(e) => setHash(e.target.value)} />
          </label>
          <label className="mt-3 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} /> I understand this records
            my approval
          </label>
          <p className={`mt-3 text-sm ${check.ok ? "t-ok" : "t-muted"}`} aria-live="polite">
            {check.reason}
          </p>
          {m.error && <p className="t-bad text-sm">{plainText((m.error as Error).message, 300)}</p>}
          <div className="mt-4 flex gap-2">
            <button
              type="button"
              className="btn btn-primary"
              disabled={!check.ok || m.isPending}
              onClick={() => m.mutate()}
            >
              Approve this step
            </button>
            <Dialog.Close className="btn">Cancel</Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function ClaimsPage() {
  const q = useQuery({ queryKey: ["claims"], queryFn: api.claims });
  if (q.isLoading) return <Loading what="claims" />;
  if (q.error) return <ErrorState error={q.error} />;
  const c = q.data as any;
  return (
    <>
      <Card title="Claims we must not make" className="mb-4">
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {(c.must_not_claim as string[]).map((x) => (
            <li key={x}>
              <Badge value="BLOCKED" /> {x}
            </li>
          ))}
        </ul>
      </Card>
      <Card title="Not tested" className="mb-4">
        <p className="text-sm">
          Real bank systems or networks; per-service integration (KMS, JWT stacks); NIST KAT vectors; network-level
          overhead; human review of the AI-drafted labels.
        </p>
      </Card>
      <StatusCard status={c.status} source={c.source} />
      {c.markdown && (
        <Card title="Claims register (read-only text)">
          <pre
            className="max-h-[60vh] overflow-auto text-xs whitespace-pre-wrap"
            tabIndex={0}
            aria-label="Claims register text"
          >
            {plainText(c.markdown, 60000)}
          </pre>
        </Card>
      )}
      <SourceFooter sources={[c.source]} />
    </>
  );
}

export function AuditPage() {
  const q = useQuery({ queryKey: ["audit"], queryFn: api.audit });
  const [res, setRes] = useState<{ valid: boolean; entries: number; first_bad_id: number | null } | null>(null);
  if (q.isLoading) return <Loading what="audit log" />;
  if (q.error) return <ErrorState error={q.error} />;
  const a = q.data as any;
  return (
    <>
      <Card
        title={`Audit log (${a.total} entries, hash-chained, append-only)`}
        actions={
          <button type="button" className="btn" onClick={async () => setRes(await api.verifyAudit())}>
            Verify chain
          </button>
        }
        className="mb-4"
      >
        {res && (
          <p aria-live="polite">
            <Badge value={res.valid ? "PASS" : "FAIL"} />{" "}
            {res.valid
              ? `chain valid across ${res.entries} entries`
              : `tampering detected at entry ${res.first_bad_id}`}
          </p>
        )}
        <div className="overflow-auto" tabIndex={0} role="region" aria-label="Scrollable table">
          <table className="dtable">
            <thead>
              <tr>
                {["#", "Time (UTC)", "Actor", "Role", "Action", "Target", "Result", "Hash"].map((h) => (
                  <th key={h} scope="col">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(a.entries as any[]).map((e) => (
                <tr key={e.id}>
                  <td className="num">{e.id}</td>
                  <td className="mono text-xs">{e.ts}</td>
                  <td>{plainText(e.actor, 64)}</td>
                  <td>{e.role}</td>
                  <td>{plainText(e.action, 64)}</td>
                  <td className="text-xs">{plainText(e.target, 120)}</td>
                  <td>
                    <Badge
                      value={
                        e.result === "ok"
                          ? "PASS"
                          : e.result === "queued"
                            ? "PROPOSED"
                            : e.result === "forbidden" || e.result === "denied" || e.result === "refused"
                              ? "FAIL"
                              : "UNKNOWN"
                      }
                      title={e.result}
                    />
                  </td>
                  <td className="mono text-xs">{String(e.entry_hash).slice(0, 12)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}

export function SettingsPage({ me }: { me: Me }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const m = useMutation({ mutationFn: api.putSettings, onSuccess: () => qc.invalidateQueries() });
  if (q.isLoading) return <Loading what="settings" />;
  if (q.error) return <ErrorState error={q.error} />;
  const s = q.data as any;
  const can = me.role === "approver";
  return (
    <Card title="Settings">
      {!can && <Notice tone="info">Changing settings requires the approver role.</Notice>}
      <dl className="m-0 grid grid-cols-[auto_1fr] items-center gap-x-4 gap-y-3 text-sm">
        <dt>Data mode</dt>
        <dd className="m-0 flex flex-wrap items-center gap-2">
          {(["LIVE", "DEMO"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              className={`btn ${s.data_mode === mode ? "btn-primary" : ""}`}
              disabled={!can}
              aria-pressed={s.data_mode === mode}
              onClick={() => m.mutate({ data_mode: mode })}
            >
              {mode}
            </button>
          ))}
          <span className="t-muted">
            DEMO reads the frozen snapshot {s.demo_snapshot ?? "(none yet)"}; jobs and approvals are disabled.
          </span>
        </dd>
        <dt>Cloud AI for custom scans</dt>
        <dd className="m-0 flex items-center gap-2">
          <Badge
            value={s.cloud_for_custom_scans ? "VERIFIED" : "BLOCKED"}
            title={s.cloud_for_custom_scans ? "ON" : "OFF"}
          />{" "}
          {s.cloud_for_custom_scans ? "ON" : "OFF (default)"}
          <button
            type="button"
            className="btn"
            disabled={!can}
            onClick={() => m.mutate({ cloud_for_custom_scans: !s.cloud_for_custom_scans })}
          >
            Toggle
          </button>
        </dd>
        <dt>Scan roots (allow-list)</dt>
        <dd className="m-0 mono text-xs">
          {Object.entries(s.scan_roots ?? {})
            .map(([k, v]) => `${k} → ${String(v)}`)
            .join(" · ")}
        </dd>
      </dl>
      {m.error && <p className="t-bad text-sm">{plainText((m.error as Error).message, 300)}</p>}
      <p className="t-muted mt-4 text-xs">
        Theme, reduced transparency, high contrast and reduced motion are personal display settings in the top bar
        (stored in this browser only).
      </p>
      <p className="t-muted text-xs">Status words follow one vocabulary; anything else shows as {normStatus("x")}.</p>
    </Card>
  );
}
