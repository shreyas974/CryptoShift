import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQuery } from "@tanstack/react-query";
import cytoscape from "cytoscape";
import { useEffect, useRef, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type AskResult, type Me } from "../api/client";
import {
  Badge,
  BarList,
  Card,
  ErrorState,
  Evidence,
  Loading,
  Notice,
  SourceFooter,
  StatusCard,
} from "../components/ui";
import { plainText } from "../lib/status";

/* eslint-disable @typescript-eslint/no-explicit-any */

const EDGE_STYLE: Record<string, { line: "solid" | "dashed" | "dotted"; color: string }> = {
  OBSERVED: { line: "solid", color: "#56d364" },
  DECLARED: { line: "dashed", color: "#aeb9cc" },
  INFERRED: { line: "dotted", color: "#e3b341" },
};

function Graph({ nodes, edges, theme }: { nodes: string[]; edges: any[]; theme: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const text = theme === "light" ? "#0f1726" : "#e8edf6";
    const cy = cytoscape({
      container: ref.current,
      elements: [
        ...nodes.map((n) => ({ data: { id: n, label: n } })),
        ...edges.map((e, i) => ({
          data: { id: `e${i}`, source: e.upstream, target: e.downstream, prov: e.provenance },
        })),
      ],
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            color: text,
            "font-size": 11,
            "background-color": "#2349b8",
            "text-valign": "bottom",
            "text-margin-y": 6,
            width: 22,
            height: 22,
          },
        },
        ...Object.entries(EDGE_STYLE).map(([prov, s]) => ({
          selector: `edge[prov = "${prov}"]`,
          style: {
            "line-style": s.line,
            "line-color": s.color,
            "target-arrow-color": s.color,
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            width: 2,
          },
        })),
      ] as any,
      layout: { name: "circle", padding: 30 },
      userZoomingEnabled: false,
      boxSelectionEnabled: false,
    });
    return () => cy.destroy();
  }, [nodes, edges, theme]);
  return (
    <div
      ref={ref}
      className="h-[380px] w-full"
      role="img"
      aria-label="Dependency graph; the same edges are listed in the table below"
    />
  );
}

export function DependenciesPage({ theme }: { theme: string }) {
  const q = useQuery({ queryKey: ["graph"], queryFn: api.graph });
  if (q.isLoading) return <Loading what="dependency graph" />;
  if (q.error) return <ErrorState error={q.error} />;
  const g = q.data as any;
  return (
    <>
      <StatusCard status={g.status} source={g.source} />
      <Card title="Dependency graph (arrow = provider → consumer)" className="mb-4">
        <p className="text-sm">
          Legend: <Badge value="OBSERVED" /> solid green = evidence in a file with a line · <Badge value="DECLARED" />{" "}
          dashed grey = synthetic descriptor only · <Badge value="INFERRED" /> dotted amber = assumption with a reason.
        </p>
        <Graph nodes={g.nodes} edges={g.edges} theme={theme} />
      </Card>
      <Card title="Edges (text list)" className="mb-4">
        <table className="dtable">
          <thead>
            <tr>
              {["Edge", "Provenance", "Kind", "File:line", "Reason"].map((h) => (
                <th key={h} scope="col">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(g.edges as any[]).map((e, i) => (
              <tr key={i}>
                <td>
                  {e.upstream} → {e.downstream}
                </td>
                <td>
                  <Badge value={e.provenance} />
                </td>
                <td className="text-xs">{e.kind || "–"}</td>
                <td className="mono text-xs">
                  {e.line ? `${plainText(e.file, 120)}:${e.line}` : plainText(e.file, 120) || "–"}
                </td>
                <td className="text-xs">{plainText(e.reason, 200)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title={`Cycles: ${g.cycles.length}`}>
          {g.cycles.length ? JSON.stringify(g.cycles) : <span className="t-muted">none</span>}
        </Card>
        <Card title={`Conflicts: ${g.conflicts.length}`}>
          <ul className="m-0 pl-4 text-sm">
            {(g.conflicts as any[]).map((c, i) => (
              <li key={i}>
                {c.upstream} → {c.downstream}: {plainText(c.issue, 200)}
              </li>
            ))}
          </ul>
        </Card>
        <Card title={`UNKNOWN references: ${g.unknown_endpoints.length}`}>
          {g.unknown_endpoints.length ? (
            <ul className="m-0 pl-4 text-sm">
              {(g.unknown_endpoints as any[]).map((u, i) => (
                <li key={i}>{plainText(`${u.service} → ${u.endpoint} (${u.file}:${u.line})`, 200)}</li>
              ))}
            </ul>
          ) : (
            <span className="t-muted">none on the demo bank (the multi-service fixture shows 3)</span>
          )}
        </Card>
      </div>
      <SourceFooter sources={[g.source, g.fixture?.source]} />
    </>
  );
}

export function EvaluationPage() {
  const q = useQuery({ queryKey: ["evaluation"], queryFn: api.evaluation });
  if (q.isLoading) return <Loading what="evaluation" />;
  if (q.error) return <ErrorState error={q.error} />;
  const e = q.data as any;
  const held = (e.sets as any[]).find((s) => s.key === "eval_held_out");
  return (
    <>
      <Notice>{e.notice}</Notice>
      <Card title="Detection sets (kept separate)" className="mb-4">
        <div className="overflow-auto" tabIndex={0} role="region" aria-label="Scrollable table">
          <table className="dtable">
            <thead>
              <tr>
                {["Set", "Repos", "Positives", "TP", "FP", "FN", "Precision", "Recall", "Status"].map((h) => (
                  <th key={h} scope="col">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(e.sets as any[]).map((s) => (
                <tr key={s.key}>
                  <td>
                    <Evidence source={s.source} label={s.name}>
                      {s.name}
                    </Evidence>
                  </td>
                  <td className="num">{s.repositories.length || "–"}</td>
                  <td className="num">{s.labels?.positive ?? "–"}</td>
                  <td className="num">{s.counts?.TP ?? "–"}</td>
                  <td className="num">{s.counts?.FP ?? "–"}</td>
                  <td className="num">{s.counts?.FN ?? "–"}</td>
                  <td className="num">{s.precision ?? "–"}</td>
                  <td className="num">{s.recall ?? "–"}</td>
                  <td className="text-xs">
                    {s.status !== "ok" ? `file ${s.status}` : plainText(s.measurement_status, 120)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-sm">
          <Badge value="SYNTHETIC" /> Synthetic smoke test: {e.synthetic_smoke_test.result}.
        </p>
      </Card>
      {held?.status === "ok" && (
        <Card title="Held-out round 2 per repository" className="mb-4">
          <BarList
            title="True positives found vs missed per held-out repository (AI-draft labels)"
            rows={Object.entries(held.per_source as Record<string, any>).flatMap(([repo, c]) => [
              { label: `${repo} TP`, value: c.TP ?? 0, tone: "ok" },
              { label: `${repo} FN`, value: c.FN ?? 0, tone: "bad" },
            ])}
          />
          <p className="t-muted mt-2 text-sm">
            Recall is low because of coverage gaps (nginx .tmpl templates, cipher lists in Python tuples, JWS names in
            constructors, Java enums/KeyFactory, pyproject dependencies), with 0 false positives. Not tuned after the
            run.
          </p>
        </Card>
      )}
      <Card title="CryptoAPI-Bench (Java, mapped subset)">
        <StatusCard status={e.cryptoapi_bench.status} source={e.cryptoapi_bench.source} />
        {e.cryptoapi_bench.data?.sentence && <Notice tone="info">{e.cryptoapi_bench.data.sentence}</Notice>}
        {e.cryptoapi_bench.data?.per_group && (
          <table className="dtable">
            <thead>
              <tr>
                {["Group", "TP", "FP", "FN", "TN", "Precision", "Recall"].map((h) => (
                  <th key={h} scope="col">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                ...Object.entries(e.cryptoapi_bench.data.per_group as Record<string, any>),
                ["OVERALL", e.cryptoapi_bench.data.overall],
              ].map(([g, m]: any) => (
                <tr key={g}>
                  <td>{g}</td>
                  {["TP", "FP", "FN", "TN", "precision", "recall"].map((k) => (
                    <td key={k} className="num">
                      {m?.[k] ?? "–"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      <SourceFooter sources={(e.sets as any[]).map((s) => s.source)} />
    </>
  );
}

export function SourcesPage() {
  const q = useQuery({ queryKey: ["sources"], queryFn: api.sources });
  if (q.isLoading) return <Loading what="data sources" />;
  if (q.error) return <ErrorState error={q.error} />;
  const s = q.data as any;
  const reg = s.registry?.data;
  const items: any[] = Array.isArray(reg?.datasets)
    ? reg.datasets
    : Array.isArray(reg)
      ? reg
      : reg
        ? Object.entries(reg).map(([id, v]: any) => ({ id, ...(typeof v === "object" ? v : { value: v }) }))
        : [];
  return (
    <>
      {(s.notices as string[]).map((n) => (
        <Notice key={n} tone="info">
          {n}
        </Notice>
      ))}
      <Card title="Dataset registry" className="mb-4">
        <StatusCard status={s.registry.status} source={s.registry.source} />
        <div className="overflow-auto" tabIndex={0} role="region" aria-label="Scrollable table">
          <table className="dtable">
            <thead>
              <tr>
                {["ID", "Type / kind", "Licence", "Notes"].map((h) => (
                  <th key={h} scope="col">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((d, i) => (
                <tr key={d.id ?? i}>
                  <td>{plainText(d.id ?? d.name ?? i, 80)}</td>
                  <td>{plainText(d.type ?? d.kind ?? d.classification ?? "–", 80)}</td>
                  <td>{plainText(d.license ?? d.licence ?? "–", 60)}</td>
                  <td className="text-xs">{plainText(d.description ?? d.notes ?? d.status ?? "", 200)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <Card title="Public repositories used for labels (pinned commits; code not committed)">
        <table className="dtable">
          <thead>
            <tr>
              {["Repository", "Split", "Licence", "Commit", "Files"].map((h) => (
                <th key={h} scope="col">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(s.public_repos as any[]).map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{r.split}</td>
                <td>{r.license}</td>
                <td className="mono text-xs">{r.commit}</td>
                <td className="num">{r.files}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <SourceFooter sources={[s.registry.source]} />
    </>
  );
}

export function MlAiPage({ me }: { me: Me }) {
  const q = useQuery({ queryKey: ["ml"], queryFn: api.ml });
  const st = useQuery({ queryKey: ["assistant-status"], queryFn: api.assistantStatus });
  const [open, setOpen] = useState(false);
  if (q.isLoading) return <Loading what="ML results" />;
  if (q.error) return <ErrorState error={q.error} />;
  const m = q.data as any;
  const cesnet = m.cesnet.metrics
    ? Object.entries(m.cesnet.metrics as Record<string, any>).map(([k, v]) => ({
        name: k.replaceAll("_", " "),
        accuracy: v.accuracy,
        macroF1: v.macro_f1,
      }))
    : [];
  return (
    <>
      <Card title="Track A: CESNET service category (traffic demo)" className="mb-4">
        <Notice tone="sim">{m.cesnet.notice}</Notice>
        <StatusCard status={m.cesnet.status} source={m.cesnet.source} />
        {cesnet.length > 0 && (
          <figure className="m-0">
            <div className="h-[260px]" aria-hidden="true">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={cesnet}>
                  <CartesianGrid strokeOpacity={0.15} />
                  <XAxis dataKey="name" tick={{ fill: "currentColor", fontSize: 12 }} />
                  <YAxis domain={[0, 1]} tick={{ fill: "currentColor", fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="accuracy" fill="#8ab4ff" isAnimationActive={false} />
                  <Bar dataKey="macroF1" name="macro F1" fill="#c9a8ff" isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <figcaption className="t-muted text-sm">Model vs majority and rule baselines (test days only)</figcaption>
            <details className="text-sm">
              <summary className="cursor-pointer">Data behind this chart</summary>
              <table className="dtable">
                <tbody>
                  {cesnet.map((r) => (
                    <tr key={r.name}>
                      <th scope="row">{r.name}</th>
                      <td className="num">accuracy {r.accuracy}</td>
                      <td className="num">macro F1 {r.macroF1}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          </figure>
        )}
      </Card>
      <Card title="Track B: finding-purpose triage" className="mb-4">
        <StatusCard status={m.triage.status} source={m.triage.source} />
        {m.triage.metrics && (
          <BarList
            title={`Macro F1, leave-one-repository-out (${m.triage.rows} rows)`}
            max={1}
            rows={Object.entries(m.triage.metrics as Record<string, any>).map(([k, v]) => ({
              label: k.replaceAll("_", " "),
              value: v.macro_f1,
              tone: k === "rule_engine" ? "ok" : "accent",
            }))}
          />
        )}
        <p className="text-sm">{m.triage.decision}</p>
      </Card>
      <Card
        title="CryptoShift Assistant: cloud LLM (Sarvam) with local read-only tools"
        actions={
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setOpen(true)}
            disabled={me.role === "viewer"}
            title={me.role === "viewer" ? "requires analyst" : undefined}
          >
            Ask the assistant
          </button>
        }
      >
        <p className="text-sm">
          Cloud AI:{" "}
          <Badge value={st.data?.cloud_ai === "ON" ? "VERIFIED" : "BLOCKED"} title={st.data?.cloud_ai ?? "OFF"} />{" "}
          <strong>{st.data?.cloud_ai ?? "OFF"}</strong> · assistant service{" "}
          {st.data?.reachable
            ? "reachable"
            : "not running (answers come from the in-process template fallback; nothing leaves the machine)"}{" "}
          · key configured: {st.data?.key_configured ? "yes" : "no"} (the key itself is never shown)
        </p>
        <table className="dtable">
          <thead>
            <tr>
              {["Run", "Passed (v2)", "Passed (v3, stricter)", "Usage"].map((h) => (
                <th key={h} scope="col">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>TEMPLATE_FALLBACK</td>
              <td className="num">
                {m.assistant_eval.template.passed ?? "–"}/{m.assistant_eval.template.n ?? 24}
              </td>
              <td className="num">
                {m.assistant_eval.template.passed ?? "–"}/{m.assistant_eval.template.n ?? 24}
              </td>
              <td>Rs 0 (no cloud)</td>
            </tr>
            <tr>
              <td>SARVAM_CLOUD live run (sarvam-105b)</td>
              <td className="num">{m.assistant_eval.sarvam.passed_v2 ?? "–"}/24</td>
              <td className="num">{m.assistant_eval.sarvam.passed_v3 ?? "–"}/24</td>
              <td className="text-xs">
                {m.assistant_eval.sarvam.usage
                  ? `${m.assistant_eval.sarvam.usage.requests} requests, est. Rs ${m.assistant_eval.sarvam.usage.estimated_cost_inr}`
                  : "–"}
              </td>
            </tr>
          </tbody>
        </table>
        <p className="t-muted text-xs">{m.assistant_eval.sarvam.note}</p>
      </Card>
      <AssistantDrawer open={open} onClose={() => setOpen(false)} />
      <SourceFooter sources={[m.cesnet.source, m.triage.source, m.assistant_eval.template.source]} />
    </>
  );
}

function AssistantDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [q, setQ] = useState("Which gates block ledger_audit?");
  const [log, setLog] = useState<{ q: string; r: AskResult }[]>([]);
  const ask = useMutation({
    mutationFn: api.ask,
    onSuccess: (r, question) => setLog((l) => [{ q: question, r }, ...l].slice(0, 10)),
  });
  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/30" />
        <Dialog.Content
          className="glass glass-overlay fixed top-4 right-4 bottom-4 z-50 flex w-[min(520px,94vw)] flex-col p-5"
          aria-describedby="asst-desc"
        >
          <Dialog.Title className="mt-0 text-xl font-semibold">Ask the assistant</Dialog.Title>
          <p id="asst-desc" className="t-muted text-sm">
            Answers cite report IDs. It cannot approve, change mappings or run commands. Answers count against your rate
            limit (10/min).
          </p>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (q.trim()) ask.mutate(q.trim());
            }}
          >
            <label className="flex-1">
              <span className="sr-only">Question</span>
              <input className="input w-full" value={q} maxLength={1000} onChange={(e) => setQ(e.target.value)} />
            </label>
            <button type="submit" className="btn btn-primary" disabled={ask.isPending}>
              Ask
            </button>
          </form>
          {ask.error && <p className="t-bad text-sm">{plainText((ask.error as Error).message, 300)}</p>}
          <ol className="m-0 mt-4 flex-1 list-none overflow-auto p-0" aria-live="polite">
            {log.map((x, i) => (
              <li key={i} className="glass mb-3 rounded-xl p-3">
                <div className="text-sm font-semibold">{plainText(x.q, 300)}</div>
                <div className="my-2 flex flex-wrap gap-2 text-xs">
                  <Badge value={x.r.mode === "SARVAM_CLOUD" ? "VERIFIED" : "PLANNED"} title={x.r.mode} />{" "}
                  <span className="mono">{x.r.mode}</span>
                  {x.r.refused && <Badge value="BLOCKED" title="refused" />}
                </div>
                <p className="m-0 text-sm whitespace-pre-wrap">{plainText(x.r.answer, 4000)}</p>
                {x.r.citations.length > 0 && (
                  <p className="t-muted mono m-0 mt-1 text-xs">cites: {x.r.citations.join(", ")}</p>
                )}
                {x.r.mode_reason && <p className="t-muted m-0 mt-1 text-xs">{plainText(x.r.mode_reason, 300)}</p>}
              </li>
            ))}
          </ol>
          <Dialog.Close className="btn mt-2">Close (Esc)</Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
