import * as React from "react";
import { Link } from "react-router-dom";
import { useApi } from "../../api/client";
import type { Graph, Plan } from "../../api/types";
import { useApp } from "../../components/Shell";
import { Empty, ErrorState, Loading, PageHeader } from "../../components/ui";
import { NetworkFigure } from "../../figures/network/NetworkFigure";

export default function DependenciesPage() {
  const { repoId } = useApp();
  const [inferred, setInferred] = React.useState(true);
  const graph = useApi<Graph>(repoId ? `/api/repositories/${repoId}/graph` : null);
  const plan = useApi<Plan>(repoId ? `/api/repositories/${repoId}/plan?inferred=${inferred ? 1 : 0}` : null);
  const error = graph.error ?? plan.error;
  return (
    <>
      <PageHeader
        title="Anatomy of Banking Dependencies"
        subtitle="The services in this repository mounted on a bench in the order the backend can migrate them. Dependency-aware sequencing is a PQC-01 requirement: a service moves only after everything it relies on."
        actions={<Link className="btn" to="/planner">Migration Planner</Link>}
      />
      {!repoId ? (
        <Empty>No repository is available. If the backend is offline, start it and this page will load.</Empty>
      ) : error && !(graph.data && plan.data) ? (
        <ErrorState error={error} retry={() => (graph.reload(), plan.reload())} />
      ) : !graph.data || !plan.data ? (
        <Loading label="Loading dependency graph" />
      ) : !graph.data.nodes.length ? (
        <Empty>No services are declared for this repository, so no dependency graph exists.</Empty>
      ) : (
        <>
          {!plan.data.valid ? (
            <div className="banner banner-error" role="status">
              <strong>No valid migration order with the current edges.</strong> {plan.data.cycles.length} dependency cycle
              {plan.data.cycles.length > 1 ? "s" : ""} ({plan.data.cycles.map((c) => c.members.join(" ↔ ")).join("; ")}) block{plan.data.cycles.length > 1 ? "" : "s"} {plan.data.steps.filter((s) => s.status !== "schedulable").length} services. The conflict is shown, not hidden.
            </div>
          ) : null}
          <NetworkFigure
            key={`${inferred}`}
            graph={graph.data}
            plan={plan.data}
            toolbar={
              <label className="kv small">
                <input type="checkbox" checked={inferred} onChange={(e) => setInferred(e.target.checked)} />
                Include import-inferred edges ({plan.data.edgeCount.inferred}) alongside declared ({plan.data.edgeCount.known})
              </label>
            }
          />
        </>
      )}
    </>
  );
}
