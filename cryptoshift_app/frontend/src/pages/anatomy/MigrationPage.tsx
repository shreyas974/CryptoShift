import * as React from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useApi } from "../../api/client";
import type { Checkpoint, Patch, Run } from "../../api/types";
import { useApp } from "../../components/Shell";
import { Async, Empty, PageHeader, Loading, ErrorState } from "../../components/ui";
import { VerifyFigure } from "../../figures/verify/VerifyFigure";

export default function MigrationPage() {
  const { repoId } = useApp();
  const [params, setParams] = useSearchParams();
  const patches = useApi<Patch[]>(repoId ? `/api/repositories/${repoId}/patches` : null, 3000);
  const checkpoints = useApi<Checkpoint[]>(repoId ? `/api/repositories/${repoId}/checkpoints` : null);
  // Pin the initial choice in the URL so a status change never silently switches patches.
  React.useEffect(() => {
    const list = patches.data;
    if (!list?.length || params.get("patch")) return;
    const first = list.find((p) => p.status === "proposed") ?? list[0];
    setParams({ patch: first.id }, { replace: true });
  }, [patches.data, params, setParams]);
  return (
    <>
      <PageHeader
        title="Anatomy of a Verified Migration"
        subtitle="AI proposes, verification validates, humans approve. A candidate patch only moves along the line when the real check in front of it has passed."
        actions={<Link className="btn" to="/verification">Verification Center</Link>}
      />
      {!repoId ? (
        <Empty>No repository is available. If the backend is offline, start it and this page will load.</Empty>
      ) : (
        <Async res={patches} empty={(d) => (d.length ? null : <Empty>No candidate patches exist for this repository yet. Propose one from the Crypto Inventory.</Empty>)}>
          {(list) => {
            const chosen = list.find((p) => p.id === params.get("patch")) ?? list.find((p) => p.status === "proposed") ?? list[0];
            const checkpoint = checkpoints.data?.find((c) => c.patchId === chosen.id) ?? null;
            return (
              <PatchLine
                key={chosen.id}
                patch={chosen}
                checkpoint={checkpoint}
                toolbar={
                  <label className="kv small">
                    <span className="muted">Candidate patch</span>
                    <select className="select" value={chosen.id} onChange={(e) => setParams({ patch: e.target.value })}>
                      {list.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.file}:{p.line} · {p.fromAlgorithm} → {p.algorithms.join(", ") || "SHA-256"} · {p.status}
                        </option>
                      ))}
                    </select>
                  </label>
                }
              />
            );
          }}
        </Async>
      )}
    </>
  );
}

function PatchLine({ patch, checkpoint, toolbar }: { patch: Patch; checkpoint: Checkpoint | null; toolbar: React.ReactNode }) {
  const runId = patch.latestRun?.id;
  const running = patch.latestRun?.status === "running";
  const run = useApi<Run>(runId ? `/api/runs/${runId}` : null, running ? 1000 : undefined);
  if (runId && !run.data && run.error) return <ErrorState error={run.error} retry={run.reload} />;
  if (runId && !run.data) return <Loading label="Loading verification run" />;
  return <VerifyFigure patch={patch} run={runId ? run.data : null} checkpoint={checkpoint} toolbar={toolbar} />;
}
