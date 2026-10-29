import { useSearchParams, Link } from "react-router-dom";
import { useApi } from "../../api/client";
import type { FindingsResponse } from "../../api/types";
import { useApp } from "../../components/Shell";
import { Async, Empty, PageHeader, fmtTime } from "../../components/ui";
import { AssetFigure } from "../../figures/asset/AssetFigure";

export default function AssetPage() {
  const { repoId } = useApp();
  const [params, setParams] = useSearchParams();
  const res = useApi<FindingsResponse>(repoId ? `/api/repositories/${repoId}/findings` : null);
  return (
    <>
      <PageHeader
        title="Anatomy of a Cryptographic Asset"
        subtitle="One real finding from the inventory, taken apart into the ten fields CryptoShift tracks. Each drawer holds one field and its evidence."
        actions={<Link className="btn" to="/inventory">Crypto Inventory</Link>}
      />
      {!repoId ? (
        <Empty>No repository is available. If the backend is offline, start it and this page will load.</Empty>
      ) : (
        <Async res={res} empty={(d) => (d.findings.length ? null : <Empty>The latest scan found no cryptographic usage, so there is no asset to inspect.</Empty>)}>
          {(data) => {
            const chosen = data.findings.find((f) => f.id === params.get("finding")) ?? data.findings[0];
            return (
              <AssetFigure
                key={chosen.id}
                finding={chosen}
                toolbar={
                  <label className="kv small">
                    <span className="muted">Finding</span>
                    <select className="select" value={chosen.id} onChange={(e) => setParams({ finding: e.target.value })}>
                      {data.findings.map((f) => (
                        <option key={f.id} value={f.id}>
                          {f.risk.score} · {f.algorithm} · {f.file}:{f.line}
                        </option>
                      ))}
                    </select>
                    <span className="muted">scan {fmtTime(data.scan.at)}</span>
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
