import * as React from "react";
import { Link } from "react-router-dom";
import { useApi } from "../../api/client";
import type { Checkpoint, FindingsResponse, Graph, Patch, Plan, Run } from "../../api/types";
import { useApp } from "../../components/Shell";
import { Badge, PageHeader } from "../../components/ui";
import { QuantumScene, W as QW, H as QH } from "../../figures/quantum/QuantumArt";
import { AssetPreview, W as AW, H as AH } from "../../figures/asset/AssetArt";
import { fieldsOf } from "../../figures/asset/model";
import { NetworkPreview } from "../../figures/network/NetworkArt";
import { useNetwork } from "../../figures/network/NetworkFigure";
import { W as NW, H as NH } from "../../figures/network/layout";
import { VerifyPreview, W as VW, H as VH, carriageX } from "../../figures/verify/VerifyArt";
import { stationsOf, stopOf } from "../../figures/verify/model";

function Preview({ w, h, label, children }: { w: number; h: number; label: string; children: React.ReactNode }) {
  return (
    <div className="lab-preview iso" data-theme="light">
      <svg className="iso-svg" viewBox={`0 0 ${w} ${h}`} role="img" aria-label={label}>
        {children}
      </svg>
    </div>
  );
}

function Placeholder({ text }: { text: string }) {
  return <div className="lab-preview lab-empty">{text}</div>;
}

function LabCard({ n, title, to, blurb, module, moduleTo, state, preview }: { n: string; title: string; to: string; blurb: string; module: string; moduleTo: string; state: React.ReactNode; preview: React.ReactNode }) {
  return (
    <article className="card lab-card">
      <Link to={to} aria-label={`Explore ${title}`} className="lab-link">
        {preview}
      </Link>
      <div className="lab-body">
        <span className="small muted mono-label">Fig {n}</span>
        <h2>{title}</h2>
        <p className="muted">{blurb}</p>
        <div className="lab-meta">
          <span className="small">
            Module: <Link to={moduleTo}>{module}</Link>
          </span>
          {state}
        </div>
        <Link className="btn btn-primary" to={to} style={{ justifySelf: "start" }}>
          Explore interactively →
        </Link>
      </div>
    </article>
  );
}

export default function LabPage() {
  const { repoId } = useApp();
  const findings = useApi<FindingsResponse>(repoId ? `/api/repositories/${repoId}/findings` : null);
  const graph = useApi<Graph>(repoId ? `/api/repositories/${repoId}/graph` : null);
  const plan = useApi<Plan>(repoId ? `/api/repositories/${repoId}/plan` : null);
  const patches = useApi<Patch[]>(repoId ? `/api/repositories/${repoId}/patches` : null);
  const checkpoints = useApi<Checkpoint[]>(repoId ? `/api/repositories/${repoId}/checkpoints` : null);
  const patch = patches.data?.find((p) => p.status === "proposed" && p.latestRun) ?? patches.data?.[0] ?? null;
  const run = useApi<Run>(patch?.latestRun ? `/api/runs/${patch.latestRun.id}` : null);

  const top = findings.data?.findings[0];
  const state = (loading: boolean, error: unknown, ok: React.ReactNode) => (error ? <Badge tone="red">Backend unavailable</Badge> : loading ? <Badge>Loading…</Badge> : ok);

  return (
    <>
      <PageHeader
        title="Anatomy Studio & Physical Systems"
        subtitle="Four interactive isometric anatomy figures: an educational superconducting quantum computer cutaway plus three live operational figures drawn directly from this repository's real state."
      />
      <div className="lab-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
        <LabCard
          n="01"
          title="Quantum Computer Cutaway"
          to="/anatomy/quantum-computer"
          blurb="Superconducting dilution refrigerator cutaway explaining cryostat stages, control lines and quantum processor. Educational model explaining why Shor's algorithm impacts RSA and ECC."
          module="Educational Model"
          moduleTo="/anatomy/quantum-computer"
          state={<Badge tone="blue">Educational model · not app data</Badge>}
          preview={
            <Preview w={QW} h={QH} label="Preview of the superconducting quantum computer">
              <QuantumScene />
            </Preview>
          }
        />
        <LabCard
          n="02"
          title="Cryptographic Asset & Cabinet"
          to="/anatomy/cryptographic-asset"
          blurb={top ? `Highest-risk finding, ${top.algorithm} at ${top.file}:${top.line}, opened drawer by drawer in the evidence cabinet.` : "Scanned cryptographic usage opened into the ten fields CryptoShift tracks."}
          module="Crypto Inventory"
          moduleTo="/inventory"
          state={state(findings.loading && !findings.data, findings.error && !findings.data, <Badge tone="green">{findings.data?.findings.length ?? 0} findings scanned</Badge>)}
          preview={
            top ? (
              <Preview w={AW} h={AH} label="Preview of the evidence cabinet">
                <AssetPreview fields={fieldsOf(top)} open="evidence" />
              </Preview>
            ) : (
              <Placeholder text={findings.error ? "Backend unavailable — no finding to draw." : findings.data ? "No findings in the latest scan." : "Loading finding…"} />
            )
          }
        />
        <LabCard
          n="03"
          title="Banking Dependencies Bench"
          to="/anatomy/banking-dependencies"
          blurb="Services mounted in the order the backend can migrate them, with declared and inferred dependencies as conduits and cycles held back."
          module="Migration Planner"
          moduleTo="/planner"
          state={state(plan.loading && !plan.data, plan.error && !plan.data, plan.data?.valid ? <Badge tone="green">{plan.data.waves.length} waves · valid order</Badge> : <Badge tone="red">{plan.data?.cycles.length} cycle blocks the order</Badge>)}
          preview={graph.data && plan.data ? <NetworkPreviewBox graph={graph.data} plan={plan.data} /> : <Placeholder text={graph.error ? "Backend unavailable — no graph to draw." : "Loading graph…"} />}
        />
        <LabCard
          n="04"
          title="Verified Migration Line"
          to="/anatomy/verified-migration"
          blurb="An inspection line where a candidate patch only advances past checks that really ran and passed, up to an explicit human approval gate."
          module="Verification Center"
          moduleTo="/verification"
          state={state(patches.loading && !patches.data, patches.error && !patches.data, patch ? <Badge tone={patch.latestRun?.verdict === "verified_candidate" ? "green" : patch.latestRun?.verdict === "failed" ? "red" : "grey"}>{patch.latestRun ? (patch.latestRun.verdict ?? "running").replace("_", " ") : "not verified yet"}</Badge> : <Badge>No patches</Badge>)}
          preview={
            patch ? (
              <VerifyPreviewBox patch={patch} run={patch.latestRun ? run.data : null} checkpoint={checkpoints.data?.find((c) => c.patchId === patch.id) ?? null} />
            ) : (
              <Placeholder text={patches.error ? "Backend unavailable — no patch to draw." : "Loading patches…"} />
            )
          }
        />
      </div>
    </>
  );
}

function NetworkPreviewBox({ graph, plan }: { graph: Graph; plan: Plan }) {
  const { layout, cycleEdges } = useNetwork(graph, plan);
  return (
    <Preview w={NW} h={NH} label="Preview of the dependency bench">
      <NetworkPreview layout={layout} graph={graph} cycleEdges={cycleEdges} />
    </Preview>
  );
}

function VerifyPreviewBox({ patch, run, checkpoint }: { patch: Patch; run: Run | null; checkpoint: Checkpoint | null }) {
  const stations = stationsOf(patch, run, checkpoint);
  return (
    <Preview w={VW} h={VH} label="Preview of the inspection line">
      <VerifyPreview stations={stations} carriage={carriageX(stopOf(stations))} />
    </Preview>
  );
}
