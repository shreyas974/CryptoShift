import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useRef, useState } from "react";
import { api, type ActivityItem, type Me, type Run, type UserRow } from "../api/client";
import { DataTable } from "../components/DataTable";
import { Badge, BarList, Card, ErrorState, Loading, Notice, ScannedText } from "../components/ui";
import { plainText } from "../lib/status";

/* eslint-disable @typescript-eslint/no-explicit-any */

const runBadge = (status: string) =>
  status === "succeeded" ? "PASS" : status === "failed" || status === "timeout" ? "FAIL" : "PROPOSED";
const fmtBytes = (n: number) =>
  n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} kB`;
const STAGE_OF: Record<string, string> = {
  Inventory: "discovery",
  Relationships: "discovery",
  "CBOM-like + CycloneDX": "discovery",
  "Verification lab": "verification",
};
const when = (ts: string | null | undefined) => (ts ? ts.replace("T", " ").slice(0, 16) : "–");

// ================================================================ Datasets & runs
export function RunsPage({ me }: { me: Me }) {
  const [selected, setSelectedState] = useState<number | null>(() => {
    const m = /run=(\d+)/.exec(window.location.hash);
    return m ? Number(m[1]) : null;
  });
  // keep the open run in the address so a refresh or a shared link shows the same run
  const setSelected = (id: number | null) => {
    setSelectedState(id);
    window.history.replaceState(null, "", id === null ? "#/runs" : `#/runs?run=${id}`);
  };
  const runs = useQuery({
    queryKey: ["runs"],
    queryFn: api.runs,
    refetchInterval: (q) => ((q.state.data ?? []).some((r) => ["queued", "running"].includes(r.status)) ? 1500 : false),
  });
  return (
    <>
      {me.role === "viewer" ? (
        <Notice tone="info">Viewers can read runs. Ask an approver for the analyst role to upload a dataset.</Notice>
      ) : (
        <>
          <DemoRepoCard onStarted={(id) => setSelected(id)} />
          <UploadForm onStarted={(id) => setSelected(id)} />
        </>
      )}
      {selected !== null && <RunDetail id={selected} me={me} onDeleted={() => setSelected(null)} />}
      <Card title="All runs" className="mb-4">
        {runs.isLoading && <Loading what="runs" />}
        {runs.error && <ErrorState error={runs.error} />}
        <ul className="news-list">
          {(runs.data ?? []).map((r) => (
            <li key={r.id} className="news-item">
              <div>
                <div className="ni-tag">{r.pipeline_label}</div>
                <div className="t-muted text-xs">{when(r.created_at)}</div>
              </div>
              <div>
                <button
                  type="button"
                  className="arrow-link"
                  onClick={() => {
                    setSelected(r.id);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                >
                  Run #{r.id}: {plainText(r.dataset_name, 80)}
                </button>
                <div className="t-muted text-sm">
                  {r.file_count} files · {fmtBytes(r.total_bytes)} · by {r.created_by}
                  {r.summary?.stages?.discovery?.findings !== undefined &&
                    ` · ${String(r.summary.stages.discovery.findings)} findings`}
                </div>
              </div>
              <span>
                <Badge value={runBadge(r.status)} /> <span className="t-muted text-sm">{r.status}</span>
              </span>
            </li>
          ))}
          {runs.data?.length === 0 && <li className="t-muted p-2 text-sm">No runs yet. Upload a dataset above.</li>}
        </ul>
      </Card>
    </>
  );
}

function DemoRepoCard({ onStarted }: { onStarted: (id: number) => void }) {
  const qc = useQueryClient();
  const repos = useQuery({ queryKey: ["demo-repos"], queryFn: api.demoRepos });
  const [repo, setRepo] = useState("demo_bank");
  const [err, setErr] = useState("");
  const start = useMutation({
    mutationFn: () => api.createDemoRun(repo, "plan"),
    onSuccess: (r) => {
      void qc.invalidateQueries({ queryKey: ["runs"] });
      void qc.invalidateQueries({ queryKey: ["activity"] });
      onStarted(r.run_id);
    },
    onError: (e) => setErr(e instanceof Error ? e.message : "failed"),
  });
  return (
    <Card title="New here? Start with a demo repository" className="mb-4">
      <p className="t-muted mt-0 text-sm">
        Built-in SYNTHETIC banking repositories (no real systems or keys). One click runs discovery and the migration
        plan, about 10 seconds.
      </p>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {(repos.data ?? []).map((r) => (
          <label key={r.id} className="choice">
            <input
              type="radio"
              name="demo-repo"
              value={r.id}
              checked={repo === r.id}
              disabled={!r.available}
              onChange={() => setRepo(r.id)}
              className="mr-2"
            />
            <strong>{r.label}</strong> <Badge value="SYNTHETIC" />
            <div className="t-muted mt-1 text-sm">{r.note}</div>
            <div className="t-muted mt-1 text-xs">
              <code>{r.path}</code> · {r.files} files{r.available ? "" : " · not found in this checkout"}
            </div>
          </label>
        ))}
      </div>
      {err && (
        <p role="alert" className="t-bad text-sm">
          {plainText(err, 300)}
        </p>
      )}
      <button
        type="button"
        className="btn btn-primary mt-4"
        disabled={start.isPending || !repos.data?.some((r) => r.id === repo && r.available)}
        onClick={() => {
          setErr("");
          start.mutate();
        }}
      >
        {start.isPending ? "Starting…" : "Scan and plan this repository"}
      </button>
    </Card>
  );
}

function UploadForm({ onStarted }: { onStarted: (id: number) => void }) {
  const qc = useQueryClient();
  const pipes = useQuery({ queryKey: ["pipelines"], queryFn: api.pipelines });
  const [files, setFiles] = useState<File[]>([]);
  const [over, setOver] = useState(false);
  const [name, setName] = useState("");
  const [pipeline, setPipeline] = useState("plan");
  const [ok, setOk] = useState(false);
  const [err, setErr] = useState("");
  const [skipped, setSkipped] = useState<string[]>([]);
  const folderRef = useRef<HTMLInputElement | null>(null);
  const start = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      for (const f of files)
        fd.append("files", f, (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name);
      fd.append("pipeline", pipeline);
      fd.append("dataset_name", name);
      fd.append("authorized", String(ok));
      return api.createRun(fd);
    },
    onSuccess: (r) => {
      setSkipped(r.skipped);
      setFiles([]);
      void qc.invalidateQueries({ queryKey: ["runs"] });
      void qc.invalidateQueries({ queryKey: ["activity"] });
      onStarted(r.run_id);
    },
    onError: (e) => setErr(e instanceof Error ? e.message : "upload failed"),
  });
  const total = files.reduce((n, f) => n + f.size, 0);
  return (
    <Card title="Or analyse your own dataset" className="mb-4">
      <p className="t-muted mt-0 text-sm">
        Upload a folder of configs and source code, a .zip, or single files. Only text files are kept; .env files, keys
        and keystores are always skipped. Everything stays on this machine: runs are written under{" "}
        <code>scratch/derived/webapp/runs/</code>.
      </p>
      <div
        className={`dropzone ${over ? "is-over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          setFiles(Array.from(e.dataTransfer.files));
        }}
      >
        <div className="mb-3 text-lg font-semibold">Drop a .zip or files here</div>
        <div className="flex flex-wrap justify-center gap-2">
          <label className="btn">
            Choose folder
            <input
              ref={(el) => {
                folderRef.current = el;
                el?.setAttribute("webkitdirectory", "");
              }}
              type="file"
              multiple
              className="sr-only"
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            />
          </label>
          <label className="btn">
            Choose files or .zip
            <input
              type="file"
              multiple
              className="sr-only"
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            />
          </label>
        </div>
        <div className="t-muted mt-3 text-sm" aria-live="polite">
          {files.length ? `${files.length} file(s) selected · ${fmtBytes(total)}` : "Nothing selected (limit 20 MB)"}
          <div className="text-xs">
            Tip: a folder or a .zip keeps the folder structure, which service detection uses.
          </div>
        </div>
      </div>
      <label className="mt-4 block text-sm">
        Dataset name (optional)
        <input
          className="input mt-1 block w-full max-w-md"
          value={name}
          maxLength={120}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. payments-repo-2026-10"
        />
      </label>
      <fieldset className="mt-4 border-0 p-0">
        <legend className="mb-2 text-sm font-semibold">Pipeline</legend>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {(pipes.data ?? []).map((p) => (
            <label key={p.id} className="choice">
              <input
                type="radio"
                name="pipeline"
                value={p.id}
                checked={pipeline === p.id}
                onChange={() => setPipeline(p.id)}
                className="mr-2"
              />
              <strong>{p.label}</strong>
              <div className="t-muted mt-1 text-sm">{p.note}</div>
              <ol className="stepper mt-3">
                {p.stages.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ol>
            </label>
          ))}
        </div>
      </fieldset>
      <label className="mt-4 flex items-start gap-2 text-sm">
        <input type="checkbox" checked={ok} onChange={(e) => setOk(e.target.checked)} />
        <span>I am authorized to analyse this dataset, and it contains no real secrets.</span>
      </label>
      {err && (
        <p role="alert" className="t-bad text-sm">
          {plainText(err, 300)}
        </p>
      )}
      <button
        type="button"
        className="btn btn-primary mt-4"
        disabled={!files.length || !ok || start.isPending}
        onClick={() => {
          setErr("");
          start.mutate();
        }}
      >
        {start.isPending ? "Uploading…" : "Upload and run"}
      </button>
      {skipped.length > 0 && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer">{skipped.length} file(s) skipped on the last upload</summary>
          <ul>
            {skipped.map((s) => (
              <li key={s}>
                <ScannedText value={s} limit={200} />
              </li>
            ))}
          </ul>
        </details>
      )}
    </Card>
  );
}

function RunDetail({ id, me, onDeleted }: { id: number; me: Me; onDeleted: () => void }) {
  const qc = useQueryClient();
  const run = useQuery({
    queryKey: ["run", id],
    queryFn: () => api.run(id),
    refetchInterval: (q) => (["queued", "running"].includes(q.state.data?.status ?? "queued") ? 1000 : false),
  });
  const done = run.data && !["queued", "running"].includes(run.data.status);
  const result = useQuery({ queryKey: ["run-result", id], queryFn: () => api.runResult(id), enabled: Boolean(done) });
  const [tab, setTab] = useState<"findings" | "services" | "steps" | "edges">("findings");
  if (run.isLoading) return <Loading what={`run #${id}`} />;
  if (run.error || !run.data) return <ErrorState error={run.error} />;
  const r: Run = run.data;
  const stages = r.summary?.stages ?? {};
  const keys = Object.keys(stages);
  const res = result.data as any;
  return (
    <Card
      title={
        <>
          Run #{r.id}: {plainText(r.dataset_name, 80)}
        </>
      }
      className="mb-4"
      actions={
        <span className="flex items-center gap-2">
          <Badge value={runBadge(r.status)} />
          <span className="t-muted text-sm" aria-live="polite">
            {r.status}
          </span>
        </span>
      }
    >
      <div className="t-muted mb-3 text-sm">
        {r.pipeline_label} · {r.file_count} files ({r.skipped_count} skipped) · {fmtBytes(r.total_bytes)} · dataset
        SHA-256 <code>{r.dataset_sha256.slice(0, 16)}…</code> · by {r.created_by} at {when(r.created_at)}
      </div>
      <ol className="stepper mb-4" aria-label="Pipeline stages">
        {(r.stages ?? []).map((label) => {
          // each visible step belongs to one script stage (scripts/webapp_run.py)
          const k = STAGE_OF[label] ?? "plan";
          const st = stages[k]?.status;
          const cls = st === "failed" ? "is-failed" : st === "ok" ? "is-done" : done ? "is-skipped" : "is-active";
          return (
            <li key={label} className={cls}>
              <span aria-hidden="true">
                {cls === "is-done" ? "✓" : cls === "is-failed" ? "✕" : cls === "is-skipped" ? "–" : "…"}
              </span>{" "}
              {label}
            </li>
          );
        })}
      </ol>
      {keys.length > 0 && (
        <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          {keys.map((k) => {
            const s = stages[k] as any;
            return (
              <div key={k} className="glass rounded-xl p-3">
                <div className="eyebrow">{k}</div>
                <div className="my-2">
                  <Badge value={s.status === "ok" ? "PASS" : "FAIL"} />{" "}
                  <span className="t-muted text-sm">{s.seconds} s</span>
                </div>
                {k === "discovery" && s.status === "ok" && (
                  <div className="text-sm">
                    <strong className="mono text-2xl">{s.findings}</strong> findings ·{" "}
                    {Object.keys(s.services ?? {}).length} services · {s.relationships?.edges ?? 0} edges
                  </div>
                )}
                {k === "plan" && s.status === "ok" && (
                  <div className="text-sm">
                    <strong className="mono text-2xl">{s.steps}</strong> steps ·{" "}
                    {Object.entries(s.states ?? {})
                      .map(([a, b]) => `${String(b)} ${a}`)
                      .join(", ")}
                    <div className="t-muted">
                      schedule{" "}
                      {s.feasible ? `feasible, objective ${s.objective}` : "not feasible under the assumed constraints"}
                    </div>
                  </div>
                )}
                {k === "verification" && <div className="text-sm">{plainText(s.status_text ?? s.label, 200)}</div>}
                {s.error && <p className="t-bad text-sm">{plainText(s.error, 300)}</p>}
                {s.label && k !== "verification" && (
                  <div className="t-muted mt-1 text-xs">{plainText(s.label, 200)}</div>
                )}
              </div>
            );
          })}
        </div>
      )}
      {done && res && (
        <>
          <div role="tablist" aria-label="Run results" className="mb-3 flex flex-wrap gap-2">
            {(
              [
                ["findings", `Findings (${res.findings.length})`],
                ["services", `Services (${res.services.length})`],
                ["steps", `Migration steps (${res.steps.length})`],
                ["edges", `Dependencies (${res.edges.length})`],
              ] as const
            ).map(([k, l]) => (
              <button
                key={k}
                type="button"
                role="tab"
                aria-selected={tab === k}
                className={`btn text-sm ${tab === k ? "btn-primary" : ""}`}
                onClick={() => setTab(k)}
              >
                {l}
              </button>
            ))}
          </div>
          <div role="tabpanel">
            {tab === "findings" && <RunFindings rows={res.findings} />}
            {tab === "services" && (
              <BarList
                title="Findings per service (risk score is provisional, not validated)"
                rows={res.services.map((s: any) => ({ label: s.service, value: s.findings }))}
              />
            )}
            {tab === "steps" &&
              (res.steps.length ? (
                <ul className="news-list">
                  {res.steps.map((s: any) => (
                    <li key={s.service} className="news-item">
                      <Badge value={s.state} />
                      <strong>{s.service}</strong>
                      <span className="t-muted text-sm">
                        {s.gates.filter((g: any) => g.status === "PASS").length}/{s.gates.length} gates pass
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="t-muted text-sm">
                  This pipeline does not build a plan. Choose “Discovery + migration plan”.
                </p>
              ))}
            {tab === "edges" &&
              (res.edges.length ? (
                <ul className="news-list">
                  {res.edges.map((e: any, i: number) => (
                    <li key={i} className="news-item">
                      <Badge value={e.provenance} />
                      <span>
                        {e.upstream} → {e.downstream}
                      </span>
                      <ScannedText value={`${e.file}${e.line ? `:${e.line}` : ""}`} limit={120} />
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="t-muted text-sm">No dependency edges in this run.</p>
              ))}
          </div>
        </>
      )}
      {r.outputs && r.outputs.length > 0 && (
        <div className="mt-4">
          <div className="eyebrow mb-2">Outputs</div>
          <div className="flex flex-wrap gap-2">
            {r.outputs.map((o) => (
              <a
                key={o.path}
                className="btn text-sm no-underline"
                href={`/api/v1/runs/${r.id}/files/${o.path}`}
                download
              >
                ⤓ {o.path} <span className="t-muted">({fmtBytes(o.bytes)})</span>
              </a>
            ))}
          </div>
        </div>
      )}
      {r.log_tail && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer">Run log</summary>
          <pre className="mono max-h-48 overflow-auto text-xs whitespace-pre-wrap" tabIndex={0} aria-label="Run log">
            {plainText(r.log_tail, 6000)}
          </pre>
        </details>
      )}
      {me.role === "approver" && done && (
        <button
          type="button"
          className="btn mt-4 text-sm"
          onClick={async () => {
            if (!window.confirm(`Delete run #${r.id} and its files? The audit log keeps a record.`)) return;
            await api.deleteRun(r.id);
            void qc.invalidateQueries({ queryKey: ["runs"] });
            onDeleted();
          }}
        >
          Delete run
        </button>
      )}
    </Card>
  );
}

type RunFinding = {
  service_id: string;
  file_path: string;
  line_number: number;
  algorithm_family: string;
  operation_purpose: string;
  target_pqc_algorithm: string;
  confidence: string;
  snippet_redacted: string;
};
function RunFindings({ rows }: { rows: RunFinding[] }) {
  const cols: ColumnDef<RunFinding, unknown>[] = [
    { accessorKey: "service_id", header: "Service" },
    {
      id: "where",
      header: "File",
      accessorFn: (r) => `${r.file_path}:${r.line_number}`,
      cell: (c) => <ScannedText value={c.getValue()} limit={90} />,
    },
    { accessorKey: "algorithm_family", header: "Family" },
    {
      accessorKey: "operation_purpose",
      header: "Purpose",
      cell: (c) =>
        c.getValue() === "unknown" ? (
          <span>
            <Badge value="HOLD" /> unknown
          </span>
        ) : (
          String(c.getValue())
        ),
    },
    { accessorKey: "confidence", header: "Confidence" },
    {
      accessorKey: "target_pqc_algorithm",
      header: "Candidate (for review)",
      cell: (c) => plainText(c.getValue(), 120),
    },
  ];
  return <DataTable data={rows} columns={cols} caption="Findings in the uploaded dataset" height={420} />;
}

// ================================================================ Users & roles
export function UsersPage({ me }: { me: Me }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["users"], queryFn: api.users, enabled: me.role === "approver" });
  const [form, setForm] = useState({ username: "", role: "viewer", password: "" });
  const [msg, setMsg] = useState<{ tone: "ok" | "bad"; text: string } | null>(null);
  if (me.role !== "approver") return <Notice tone="info">Only approvers can manage users.</Notice>;
  const done = (text: string) => {
    setMsg({ tone: "ok", text });
    void qc.invalidateQueries({ queryKey: ["users"] });
    void qc.invalidateQueries({ queryKey: ["activity"] });
  };
  const fail = (e: unknown) => setMsg({ tone: "bad", text: e instanceof Error ? e.message : "failed" });
  return (
    <>
      <Card title="Add a user" className="mb-4">
        <form
          className="grid grid-cols-1 items-end gap-3 md:grid-cols-[1fr_180px_1fr_auto]"
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              await api.addUser(form.username, form.role, form.password);
              setForm({ username: "", role: "viewer", password: "" });
              done(`Added ${form.username}.`);
            } catch (ex) {
              fail(ex);
            }
          }}
        >
          <label className="text-sm">
            Username
            <input
              className="input mt-1 block w-full"
              value={form.username}
              pattern="[A-Za-z0-9_.\-]{3,64}"
              required
              autoComplete="off"
              onChange={(e) => setForm({ ...form, username: e.target.value })}
            />
          </label>
          <label className="text-sm">
            Role
            <select
              className="input mt-1 block w-full"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
            >
              <option value="viewer">viewer</option>
              <option value="analyst">analyst</option>
              <option value="approver">approver</option>
            </select>
          </label>
          <label className="text-sm">
            Initial password (12+ characters)
            <input
              className="input mt-1 block w-full"
              type="password"
              minLength={12}
              required
              autoComplete="new-password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </label>
          <button type="submit" className="btn btn-primary">
            Add user
          </button>
        </form>
        <p className="t-muted mb-0 text-xs">
          viewer: reads everything · analyst: also runs pipelines, scans and the assistant · approver: also approves
          READY steps, manages users and settings.
        </p>
      </Card>
      {msg && (
        <p role="status" className={`t-${msg.tone} text-sm`}>
          {plainText(msg.text, 200)}
        </p>
      )}
      <Card title="People">
        {q.isLoading && <Loading what="users" />}
        {q.error && <ErrorState error={q.error} />}
        <table className="dtable">
          <caption className="sr-only">Local user accounts</caption>
          <thead>
            <tr>
              <th scope="col">User</th>
              <th scope="col">Role</th>
              <th scope="col">Status</th>
              <th scope="col">Created</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(q.data ?? []).map((u: UserRow) => (
              <tr key={u.id}>
                <td>
                  <strong>{u.username}</strong> {u.username === me.username && <span className="t-muted">(you)</span>}
                </td>
                <td>
                  <select
                    className="input"
                    aria-label={`Role for ${u.username}`}
                    value={u.role}
                    onChange={(e) =>
                      api
                        .updateUser(u.id, { role: e.target.value })
                        .then(() => done(`Changed ${u.username}'s role.`), fail)
                    }
                  >
                    <option value="viewer">viewer</option>
                    <option value="analyst">analyst</option>
                    <option value="approver">approver</option>
                  </select>
                </td>
                <td>
                  {u.disabled ? <Badge value="BLOCKED" title="disabled" /> : <Badge value="VERIFIED" title="active" />}
                </td>
                <td className="num">{when(u.created_at)}</td>
                <td className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="btn text-xs"
                    onClick={() =>
                      api
                        .updateUser(u.id, { disabled: !u.disabled })
                        .then(() => done(`${u.disabled ? "Enabled" : "Disabled"} ${u.username}.`), fail)
                    }
                  >
                    {u.disabled ? "Enable" : "Disable"}
                  </button>
                  <button
                    type="button"
                    className="btn text-xs"
                    onClick={() => {
                      const pw = window.prompt(`New password for ${u.username} (12+ characters)`);
                      if (pw)
                        api
                          .updateUser(u.id, { password: pw })
                          .then(() => done(`Reset ${u.username}'s password.`), fail);
                    }}
                  >
                    Reset password
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="t-muted mb-0 text-xs">
          Every change is written to the audit log. You cannot demote or disable yourself, and one active approver
          always remains.
        </p>
      </Card>
    </>
  );
}

// ================================================================ Activity
export function ActivityPage() {
  const q = useQuery({ queryKey: ["activity", 100], queryFn: () => api.activity(100), refetchInterval: 15_000 });
  if (q.isLoading) return <Loading what="activity" />;
  if (q.error || !q.data) return <ErrorState error={q.error} />;
  return (
    <Card>
      <ActivityList items={q.data.items} />
    </Card>
  );
}

export function ActivityList({ items }: { items: ActivityItem[] }) {
  return (
    <ul className="news-list">
      {items.map((i) => (
        <li key={i.id} className="news-item">
          <div>
            <div className="ni-tag">{i.action.split(".")[0]}</div>
            <div className="t-muted text-xs">{when(i.ts)}</div>
          </div>
          <div>{plainText(i.title, 160)}</div>
          <Badge
            value={i.result === "ok" || i.result === "queued" ? "PASS" : i.result === "denied" ? "FAIL" : "BLOCKED"}
            title={i.result}
          />
        </li>
      ))}
      {!items.length && <li className="t-muted p-2 text-sm">No activity yet.</li>}
    </ul>
  );
}

// ================================================================ Reports (print to PDF)
export function ReportsPage() {
  const q = useQuery({ queryKey: ["full-report"], queryFn: api.fullReport });
  if (q.isLoading) return <Loading what="report" />;
  if (q.error || !q.data) return <ErrorState error={q.error} />;
  const r = q.data as any;
  const o = r.overview;
  const p = r.plan;
  const v = r.verification;
  const a = r.approvals;
  return (
    <div className="print-root">
      <div className="no-print mb-4 flex flex-wrap gap-2">
        <button type="button" className="btn btn-primary" onClick={() => window.print()}>
          Save as PDF / print
        </button>
        <a className="btn no-underline" href="/api/v1/export/md?page=plan" download>
          ⤓ Plan (Markdown)
        </a>
        <a className="btn no-underline" href="/api/v1/export/json?page=verification" download>
          ⤓ Verification (JSON)
        </a>
      </div>
      <Card className="mb-4">
        <div className="eyebrow">CryptoShift migration report</div>
        <h2 className="h-section">Post-quantum migration: status and evidence</h2>
        <p className="t-muted text-sm">
          Generated {r.generated_utc} by {r.by} · data mode {r.data_mode} · plan hash{" "}
          <code>{o.plan_hash?.slice(0, 16) ?? "–"}</code> · audit chain{" "}
          {r.audit.valid ? `valid (${r.audit.entries} entries)` : `BROKEN at entry ${r.audit.first_bad_id}`}
        </p>
        <Notice>
          Hackathon prototype. Synthetic demo bank; TLS results are a loopback TEST SCENARIO with throw-away keys. Not
          production ready, not certified, no quantum-safety guarantee. Candidates are for human review.
        </Notice>
      </Card>
      <Card title="1. Pipeline status" className="mb-4">
        <table className="dtable">
          <tbody>
            {o.stages.map((s: any) => (
              <tr key={s.name}>
                <th scope="row">{s.name}</th>
                <td>
                  <Badge value={s.status} />
                </td>
                <td>{plainText(s.note, 200)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <Card title="2. Migration plan" className="mb-4">
        <p className="text-sm">
          Objective {p.objective ?? "–"} · {p.dependency_violations} dependency violations · risk score is provisional,
          not validated.
        </p>
        <table className="dtable">
          <thead>
            <tr>
              <th scope="col">Wave</th>
              <th scope="col">Service</th>
              <th scope="col">Risk</th>
              <th scope="col">Candidates (for review)</th>
            </tr>
          </thead>
          <tbody>
            {p.tasks.map((t: any) => (
              <tr key={t.service}>
                <td className="num">{t.wave ?? "–"}</td>
                <td>{t.service}</td>
                <td className="num">{t.risk}</td>
                <td>{plainText(t.candidates.join("; "), 200)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {p.comparison && (
          <p className="t-muted text-sm">
            Baseline {p.comparison.baseline.objective}; QpiAI Opt {p.comparison.qpiai_opt.objective ?? "–"} (
            {p.comparison.qpiai_opt.verdict}); QCloud QAOA {p.comparison.qcloud_qaoa.verdict}.
          </p>
        )}
      </Card>
      <Card title="3. Verification gates" className="mb-4 print-page-break">
        <p className="t-muted text-sm">{v.label}</p>
        <table className="dtable">
          <tbody>
            {v.steps.map((s: any) => (
              <tr key={s.step_id}>
                <th scope="row">{s.service}</th>
                <td>
                  <Badge value={s.state} />
                </td>
                <td>
                  {s.gates.filter((g: any) => g.status === "PASS").length}/{s.gates.length} gates pass
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <Card title="4. Approvals" className="mb-4">
        <p className="text-sm">
          {a.approved_steps.length} approved of {a.steps.length} steps · {a.invalidated.length} invalidated by plan
          changes. Approval is human-only and bound to the plan hash.
        </p>
      </Card>
      <Card title="5. What this report does not claim" className="mb-4">
        <ul className="text-sm">
          {r.must_not_claim.map((c: string) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
