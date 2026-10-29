import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useApi, mutate, ApiError } from "../api/client";
import type { AuditEntry, FindingsResponse, Graph, Patch, Plan, Repository } from "../api/types";
import { useApp } from "../components/Shell";
import { Async, Badge, BasisBadge, Card, Empty, Field, PageHeader, RiskBadge, SearchBox, VerdictBadge, fmtTime } from "../components/ui";
import { AssetFigure } from "../figures/asset/AssetFigure";
import { NetworkFigure } from "../figures/network/NetworkFigure";
import { DonutChart, BarChart, WaveVisualizer } from "../components/VisualCharts";

const useFindings = () => {
  const { repoId } = useApp();
  return useApi<FindingsResponse>(repoId ? `/api/repositories/${repoId}/findings` : null);
};

const NoRepo = () => <Empty>No repository is available. Choose one in the top bar, or start the backend if it is offline.</Empty>;

// ---------------- Overview & Enterprise Landing ----------------
export function Overview() {
  const { repoId } = useApp();
  const findings = useFindings();
  const patches = useApi<Patch[]>(repoId ? `/api/repositories/${repoId}/patches` : null);
  const plan = useApi<Plan>(repoId ? `/api/repositories/${repoId}/plan` : null);
  const audit = useApi<AuditEntry[]>("/api/audit");

  if (!repoId) return <NoRepo />;

  return (
    <>
      {/* Company-Grade Sunlit Hero Header */}
      <section className="landing-hero" aria-label="Enterprise Overview">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 20 }}>
          <div style={{ flex: "1 1 560px" }}>
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 14, flexWrap: "wrap" }}>
              <span className="pill-badge pill-badge-sun">PQC-01 Banking Architecture</span>
              <span className="badge badge-green" style={{ fontSize: 12 }}>● Live Monorepo Connected</span>
              <span className="badge badge-amber" style={{ fontSize: 12 }}>NIST FIPS 203/204 Target</span>
            </div>
            <h1>Verification-Gated Cryptographic Migration</h1>
            <p style={{ marginTop: 10, fontSize: 14.5, color: "var(--cs-text-2)", lineHeight: 1.65 }}>
              Enterprise post-quantum cryptographic migration platform for mission-critical banking and financial infrastructure. Governed by a tripartite security protocol: <strong>AI proposes candidate patches</strong>, <strong>rigorous multi-stage verification validates empirically</strong>, and <strong>authenticated human reviewers deliberately approve</strong>.
            </p>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignSelf: "center" }}>
            <Link to="/inventory" className="btn btn-primary" style={{ padding: "11px 20px", fontSize: 14 }}>
              Explore Inventory & Cabinet →
            </Link>
            <Link to="/verification" className="btn" style={{ padding: "11px 18px", fontSize: 14 }}>
              Inspect Verification Line
            </Link>
            <Link to="/planner" className="btn" style={{ padding: "11px 18px", fontSize: 14 }}>
              Migration Waves
            </Link>
          </div>
        </div>

        {/* Interactive 8-Stage Migration Pipeline Bar */}
        <div className="pipeline-tracker" style={{ marginTop: 24, paddingTop: 20, borderTop: "1px solid rgba(217, 119, 6, 0.16)" }}>
          <div style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--cs-accent-strong)", marginBottom: 12 }}>
            PQC Migration Lifecycle Protocol
          </div>
          <div className="pipeline-steps">
            {[
              { num: "01", name: "Code Discovery", desc: "AST & API Scan", link: "/repositories" },
              { num: "02", name: "Asset Cabinet", desc: "10-Field Evidence", link: "/inventory" },
              { num: "03", name: "Risk Assessment", desc: "HNDL & Shor Scoring", link: "/risk" },
              { num: "04", name: "Dependency DAG", desc: "Cycle-Free Waves", link: "/planner" },
              { num: "05", name: "Candidate Synthesis", desc: "PQC Rule Engine", link: "/patches" },
              { num: "06", name: "Verification Line", desc: "Differential Testing", link: "/verification" },
              { num: "07", name: "Human Review Gate", desc: "Named Sign-off", link: "/verification" },
              { num: "08", name: "Safe Release", desc: "Byte-for-Byte Rollback", link: "/rollback" },
            ].map((step) => (
              <Link to={step.link} key={step.num} className="pipeline-step-card">
                <div className="step-num">{step.num}</div>
                <div className="step-title">{step.name}</div>
                <div className="step-desc">{step.desc}</div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Metrics Row */}
      <Async res={findings}>
        {(f) => {
          const shor = f.findings.filter((x) => x.threat.level === "shor").length;
          const critical = f.findings.filter((x) => x.risk.band === "critical").length;
          const high = f.findings.filter((x) => x.risk.band === "high").length;
          const medium = f.findings.filter((x) => x.risk.band === "medium").length;
          const low = f.findings.filter((x) => x.risk.band === "low").length;

          const p = patches.data ?? [];
          const verified = p.filter((x) => x.latestRun?.verdict === "verified_candidate").length;
          const failed = p.filter((x) => x.latestRun?.verdict === "failed").length;
          const unverified = p.filter((x) => !x.latestRun).length;

          const rsaCount = f.findings.filter((x) => x.family === "RSA").length;
          const eccCount = f.findings.filter((x) => x.family === "ECC").length;
          const aesCount = f.findings.filter((x) => x.family === "AES").length;
          const shaCount = f.findings.filter((x) => x.family === "SHA1").length;

          const riskSegments = [
            { label: "Critical Band", value: critical, color: "var(--cs-red)" },
            { label: "High Band", value: high, color: "var(--cs-accent)" },
            { label: "Medium Band", value: medium, color: "var(--cs-gold)" },
            { label: "Low Band", value: low, color: "var(--cs-green)" },
          ].filter((s) => s.value > 0);

          const algoSegments = [
            { label: "RSA (Shor Critical)", value: rsaCount, color: "var(--cs-red)" },
            { label: "ECC (Shor Vulnerable)", value: eccCount, color: "var(--cs-accent)" },
            { label: "SHA-1 / MD5", value: shaCount, color: "var(--cs-gold)" },
            { label: "AES-256 (Safe)", value: aesCount, color: "var(--cs-green)" },
          ].filter((s) => s.value > 0);

          const patchSegments = [
            { label: "Verified Candidates", value: verified, color: "var(--cs-green)" },
            { label: "Awaiting Verification", value: unverified, color: "var(--cs-gold)" },
            { label: "Failed Checks", value: failed, color: "var(--cs-red)" },
          ].filter((s) => s.value > 0);

          return (
            <>
              {/* Stat Cards */}
              <div className="grid grid-4" style={{ marginBottom: 24 }}>
                <Card>
                  <div className="stat">
                    <strong>{f.findings.length}</strong>
                    <span>Total Cryptographic Findings ({f.scan.filesScanned} files scanned)</span>
                  </div>
                </Card>
                <Card>
                  <div className="stat">
                    <strong style={{ color: "var(--cs-red)" }}>{shor}</strong>
                    <span>Quantum-Vulnerable Usages · {critical} Critical Band</span>
                  </div>
                </Card>
                <Card>
                  <div className="stat">
                    <strong style={{ color: "var(--cs-accent-strong)" }}>{p.length}</strong>
                    <span>Candidate Patches Proposed ({unverified} awaiting run)</span>
                  </div>
                </Card>
                <Card>
                  <div className="stat">
                    <strong style={{ color: "var(--cs-green)" }}>
                      {verified}
                      <span className="muted" style={{ fontSize: 16 }}> / {failed} failed</span>
                    </strong>
                    <span>Verified Migration Candidates</span>
                  </div>
                </Card>
              </div>

              {/* Visual Analytics Charts Grid */}
              <div className="grid grid-3" style={{ marginBottom: 24 }}>
                <Card title="Threat & Risk Distribution">
                  <DonutChart
                    segments={riskSegments}
                    centerLabel="Findings"
                    centerValue={f.findings.length}
                  />
                </Card>

                <Card title="Algorithm Families in Monorepo">
                  <DonutChart
                    segments={algoSegments}
                    centerLabel="Algorithms"
                    centerValue={f.findings.length}
                  />
                </Card>

                <Card title="Candidate Patch Verification">
                  <DonutChart
                    segments={patchSegments.length ? patchSegments : [{ label: "No Patches", value: 1, color: "var(--cs-border)" }]}
                    centerLabel="Patches"
                    centerValue={p.length}
                  />
                </Card>
              </div>

              {/* NIST Post-Quantum Standards Alignment Card */}
              <div style={{ marginBottom: 24 }}>
                <Card title="NIST Post-Quantum Cryptography (PQC) Standards Alignment">
                  <div className="grid grid-2" style={{ alignItems: "stretch" }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                      <p style={{ fontSize: 13.5, color: "var(--cs-text-2)", lineHeight: 1.6 }}>
                        Active inventory scan of banking microservices indicates legacy asymmetric cryptography vulnerable to Shor's algorithm and Harvest-Now-Decrypt-Later (HNDL) interception.
                      </p>
                      <BarChart
                        items={[
                          { label: "RSA Legacy (Key Exchange & Tokens)", count: rsaCount, color: "var(--cs-red)", sub: "Shor Critical" },
                          { label: "ECC / ECDSA Curves (Interbank TLS)", count: eccCount, color: "var(--cs-accent)", sub: "Shor Vulnerable" },
                          { label: "SHA-1 / MD5 Deprecated Hashes", count: shaCount, color: "var(--cs-gold)", sub: "Collision Risk" },
                          { label: "AES-256 Symmetric Encryption", count: aesCount, color: "var(--cs-green)", sub: "Grover Resistant" },
                        ]}
                      />
                    </div>

                    <div style={{ background: "rgba(254, 243, 199, 0.4)", padding: 18, borderRadius: "var(--cs-radius)", border: "1px solid var(--cs-border)", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8, color: "var(--cs-text)" }}>
                          NIST PQC Replacement Target Specifications
                        </div>
                        <ul className="list small" style={{ gap: 10 }}>
                          <li>
                            <Badge tone="blue">FIPS 203</Badge>
                            <span><strong>ML-KEM (Module-Lattice KEM):</strong> Primary standard for post-quantum public-key encryption and interbank key establishment.</span>
                          </li>
                          <li>
                            <Badge tone="green">FIPS 204</Badge>
                            <span><strong>ML-DSA (Module-Lattice DSA):</strong> Primary post-quantum digital signature algorithm for transaction signing and PKI certificates.</span>
                          </li>
                          <li>
                            <Badge tone="orange">FIPS 205</Badge>
                            <span><strong>SLH-DSA (Stateless Hash DSA):</strong> Stateless hash-based backup signatures for firmware and long-term settlement authorization.</span>
                          </li>
                        </ul>
                      </div>
                      <div className="kv" style={{ marginTop: 14 }}>
                        <Link to="/inventory" className="btn btn-small btn-primary">Open Asset Evidence Cabinet</Link>
                        <Link to="/verification" className="btn btn-small">Verification Rail</Link>
                      </div>
                    </div>
                  </div>
                </Card>
              </div>

              {/* High-Risk Findings and Plan Summary */}
              <div className="split">
                <Card
                  title="Critical Cryptographic Findings Requiring Migration"
                  actions={<Link to="/inventory" className="btn btn-small">View All in Cabinet →</Link>}
                >
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Algorithm</th>
                          <th>Location</th>
                          <th>Risk</th>
                          <th className="hide-sm">Verification</th>
                          <th>Inspect</th>
                        </tr>
                      </thead>
                      <tbody>
                        {f.findings.slice(0, 6).map((x) => (
                          <tr key={x.id}>
                            <td>
                              <strong>{x.algorithm}</strong>
                              <div className="small muted">{x.service?.name ?? "Service"}</div>
                            </td>
                            <td>
                              <Link to={`/inventory?finding=${x.id}`} className="mono">
                                {x.file}:{x.line}
                              </Link>
                            </td>
                            <td>
                              <RiskBadge risk={x.risk} />
                            </td>
                            <td className="hide-sm">
                              <VerdictBadge verdict={x.verification.status} />
                            </td>
                            <td>
                              <Link to={`/inventory?finding=${x.id}`} className="action-pill-eye" title="Inspect in Evidence Cabinet">
                                👀 Cabinet
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>

                <div>
                  <Card title="Migration Wave Schedule" actions={<Link to="/planner" className="btn btn-small">Full Planner</Link>}>
                    {plan.data ? (
                      plan.data.valid ? (
                        <div>
                          <p style={{ lineHeight: 1.6, marginBottom: 12 }}>
                            Valid dependency-aware migration order scheduled across <strong>{plan.data.waves.length} waves</strong> and {plan.data.steps.length} services without deadlocks.
                          </p>
                          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                            {plan.data.waves.map((w, idx) => (
                              <span key={idx} className="badge badge-blue">
                                Wave {idx + 1}: {w.length} services
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <p>
                          <Badge tone="red">Blocked</Badge> Cycle detected across{" "}
                          {plan.data.cycles.map((c) => c.members.join(" ↔ ")).join(", ")}.
                        </p>
                      )
                    ) : (
                      <p className="muted">Loading migration plan…</p>
                    )}
                  </Card>

                  <Card title="Recent Security Audit Ledger" actions={<Link to="/reports" className="btn btn-small">Audit Log</Link>}>
                    <ul className="list small">
                      {(audit.data ?? []).slice(0, 5).map((a) => (
                        <li key={a.id} style={{ justifyContent: "space-between" }}>
                          <span>
                            <strong>{a.action}</strong> <span className="muted">{a.detail}</span>
                          </span>
                          <span className="muted mono" style={{ fontSize: 11 }}>{fmtTime(a.at)}</span>
                        </li>
                      ))}
                    </ul>
                  </Card>
                </div>
              </div>
            </>
          );
        }}
      </Async>
    </>
  );
}

// ---------------- Repositories ----------------
export function Repositories() {
  const { setRepoId, repoId } = useApp();
  const res = useApi<Repository[]>("/api/repositories");
  const [busy, setBusy] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const act = async (label: string, path: string) => {
    setBusy(label);
    setError(null);
    try {
      await mutate(path);
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <PageHeader
        title="Repositories"
        subtitle="Repositories CryptoShift scans. Each is scanned from a working copy so released patches and rollbacks change real files."
      />
      {error ? <div className="banner banner-error">{error}</div> : null}
      <Async res={res} empty={(d) => (d.length ? null : <Empty>No repositories are registered with the backend.</Empty>)}>
        {(list) => (
          <div className="grid">
            {list.map((r) => (
              <Card
                key={r.id}
                title={<span className="mono">{r.name}</span>}
                actions={
                  <div className="kv">
                    {r.id === repoId ? <Badge tone="orange">Active</Badge> : <button className="btn btn-small" onClick={() => setRepoId(r.id)}>Select</button>}
                  </div>
                }
              >
                <p className="muted" style={{ marginBottom: 14 }}>{r.description}</p>
                <dl className="fields">
                  <Field label="Source path">{r.source}</Field>
                  <Field label="Language">{r.language}</Field>
                  <Field label="Services declared">{r.services}</Field>
                  <Field label="Last scan">{r.lastScan ? `${fmtTime(r.lastScan.at)} · ${r.lastScan.findings} findings in ${r.lastScan.filesScanned} files` : "Never scanned"}</Field>
                </dl>
                <div className="kv" style={{ marginTop: 16 }}>
                  <button className="btn btn-primary" disabled={Boolean(busy)} onClick={() => act("scan", `/api/repositories/${r.id}/scan`)}>
                    {busy === "scan" ? "Scanning…" : "Rescan Repository"}
                  </button>
                  <button
                    className="btn"
                    disabled={Boolean(busy)}
                    onClick={() => confirm("Restore the working copy from the bundled sample and discard its patches, runs and checkpoints?") && act("reset", `/api/repositories/${r.id}/reset`)}
                  >
                    Reset Working Copy
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </Async>
    </>
  );
}

// ---------------- Living Crypto Inventory with AssetFigure ----------------
export function Inventory() {
  const res = useFindings();
  const { repoId } = useApp();
  const [params, setParams] = useSearchParams();
  const [q, setQ] = React.useState(params.get("q") ?? "");
  const [band, setBand] = React.useState("all");
  const [family, setFamily] = React.useState("all");

  React.useEffect(() => setQ(params.get("q") ?? ""), [params]);

  if (!repoId) return <NoRepo />;

  const activeFindingId = params.get("finding");

  return (
    <>
      <PageHeader
        title="Crypto Inventory & Evidence Cabinet"
        subtitle="Every cryptographic usage discovered by the scanner, with exact file and line references, risk factor breakdown, and the interactive isometric Evidence Cabinet."
      />

      <Async res={res} empty={(d) => (d.findings.length ? null : <Empty>The latest scan found no cryptographic usage.</Empty>)}>
        {(d) => {
          const needle = q.toLowerCase();
          const rows = d.findings.filter(
            (f) =>
              (band === "all" || f.risk.band === band) &&
              (family === "all" || f.family === family) &&
              (!needle || [f.algorithm, f.file, f.service?.name, f.role.value, f.api].join(" ").toLowerCase().includes(needle))
          );

          // Active finding for the living isometric AssetFigure
          const currentFinding = rows.find((f) => f.id === activeFindingId) ?? rows[0] ?? null;

          return (
            <>
              {/* Living Embedded AssetFigure */}
              {currentFinding ? (
                <div style={{ marginBottom: 24 }}>
                  <Card
                    title={
                      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                        <span>Living Evidence Cabinet: <strong>{currentFinding.algorithm}</strong></span>
                        <span className="mono" style={{ fontSize: 12 }}>{currentFinding.file}:{currentFinding.line}</span>
                      </div>
                    }
                    actions={
                      <div className="kv">
                        <RiskBadge risk={currentFinding.risk} />
                        <VerdictBadge verdict={currentFinding.verification.status} />
                      </div>
                    }
                  >
                    <p style={{ fontSize: 13, color: "var(--cs-text-2)", marginBottom: 14 }}>
                      Select any drawer below to pull the physical evidence specimen from the cabinet. The cabinet animates smoothly in real-time to reflect the active finding.
                    </p>
                    <AssetFigure
                      key={currentFinding.id}
                      finding={currentFinding}
                      toolbar={
                        <label className="kv small">
                          <span className="muted">Cabinet Finding:</span>
                          <select
                            className="select"
                            value={currentFinding.id}
                            onChange={(e) => setParams({ finding: e.target.value })}
                          >
                            {rows.map((f) => (
                              <option key={f.id} value={f.id}>
                                {f.algorithm} ({f.file}:{f.line}) · {f.risk.band}
                              </option>
                            ))}
                          </select>
                        </label>
                      }
                    />
                  </Card>
                </div>
              ) : null}

              {/* Filters and Inventory Table */}
              <Card>
                <div className="filters">
                  <div style={{ flex: "1 1 280px" }}>
                    <SearchBox value={q} onChange={setQ} placeholder="Filter by algorithm, file, service or role…" />
                  </div>
                  <select aria-label="Risk band" value={band} onChange={(e) => setBand(e.target.value)} className="select">
                    <option value="all">All risk bands</option>
                    {["critical", "high", "medium", "low"].map((b) => (
                      <option key={b} value={b}>{b}</option>
                    ))}
                  </select>
                  <select aria-label="Algorithm family" value={family} onChange={(e) => setFamily(e.target.value)} className="select">
                    <option value="all">All families</option>
                    {["RSA", "ECC", "SHA1", "AES"].map((b) => (
                      <option key={b} value={b}>{b}</option>
                    ))}
                  </select>
                </div>

                <p className="small muted" style={{ marginBottom: 12 }}>
                  Showing {rows.length} of {d.findings.length} findings · Scan completed {fmtTime(d.scan.at)}
                </p>

                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Algorithm</th>
                        <th>File and Line</th>
                        <th className="hide-sm">Role</th>
                        <th className="hide-sm">Service</th>
                        <th>Risk Score</th>
                        <th className="hide-sm">Verification</th>
                        <th>Inspect</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((f) => (
                        <tr
                          key={f.id}
                          className="row-link"
                          aria-selected={currentFinding?.id === f.id}
                          tabIndex={0}
                          onClick={() => setParams({ finding: f.id })}
                          onKeyDown={(e) => e.key === "Enter" && setParams({ finding: f.id })}
                        >
                          <td>
                            <strong>{f.algorithm}</strong>
                            <div className="small muted">{f.api}</div>
                          </td>
                          <td className="mono">{f.file}:{f.line}</td>
                          <td className="hide-sm">
                            {f.role.value ?? <em className="muted">unknown</em>} <BasisBadge basis={f.role.basis} />
                          </td>
                          <td className="hide-sm">{f.service?.name ?? <em className="muted">unmapped</em>}</td>
                          <td><RiskBadge risk={f.risk} /></td>
                          <td className="hide-sm"><VerdictBadge verdict={f.verification.status} /></td>
                          <td>
                            <button
                              type="button"
                              className="action-pill-eye"
                              title="Inspect cabinet for this finding"
                              onClick={(e) => {
                                e.stopPropagation();
                                setParams({ finding: f.id });
                                window.scrollTo({ top: 0, behavior: "smooth" });
                              }}
                            >
                              👀 Inspect
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {rows.length === 0 ? <Empty>No findings match these filters.</Empty> : null}
              </Card>
            </>
          );
        }}
      </Async>
    </>
  );
}

// ---------------- Risk Assessment ----------------
export function Risk() {
  const res = useFindings();
  const { repoId } = useApp();
  if (!repoId) return <NoRepo />;

  return (
    <>
      <PageHeader
        title="Risk Assessment"
        subtitle="Each cryptographic risk score is the sum of factors listed. Missing or undeclared evidence is scored conservatively and flagged, never assumed safe."
      />
      <Async res={res}>
        {(d) => {
          const bands = ["critical", "high", "medium", "low"] as const;
          return (
            <>
              <div className="grid grid-4" style={{ marginBottom: 20 }}>
                {bands.map((b) => (
                  <Card key={b}>
                    <div className="stat">
                      <strong>{d.findings.filter((f) => f.risk.band === b).length}</strong>
                      <span style={{ textTransform: "capitalize" }}>{b} Risk Usages</span>
                    </div>
                  </Card>
                ))}
              </div>
              <Card title="Factor Scoring Breakdown">
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Finding</th>
                        <th>Scored Factors</th>
                        <th>Composite Risk</th>
                      </tr>
                    </thead>
                    <tbody>
                      {d.findings.map((f) => (
                        <tr key={f.id}>
                          <td>
                            <strong>{f.algorithm}</strong>
                            <div className="small mono">
                              <Link to={`/inventory?finding=${f.id}`}>{f.file}:{f.line}</Link>
                            </div>
                          </td>
                          <td>
                            <ul className="list small">
                              {f.risk.factors.map((x, i) => (
                                <li key={i}>
                                  <span className="mono" style={{ minWidth: 38 }}>+{x.points}</span>
                                  <span>
                                    {x.label}{" "}
                                    {x.basis === "missing" ? <Badge tone="amber">missing evidence</Badge> : null}
                                  </span>
                                </li>
                              ))}
                            </ul>
                          </td>
                          <td><RiskBadge risk={f.risk} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
              <Card title="Assessment Methodology (PQC-01)">
                <p className="small" style={{ lineHeight: 1.6 }}>
                  Point Weights: Shor-vulnerable asymmetric algorithm +40; classically weak hash +15; sub-2048-bit RSA +10; confidentiality role (harvest-now-decrypt-later vulnerability) +10, digital signature +5; internet exposure +15 / partner network +12 / internal network +5 / undeclared +8; data lifetime ≥10 y +15 / ≥3 y +8 / shorter +3 / undeclared +8; +2 per dependent service (max +10). Risk Bands: ≥70 critical, ≥50 high, ≥30 medium, &lt;30 low.
                </p>
              </Card>
            </>
          );
        }}
      </Async>
    </>
  );
}

// ---------------- Living Migration Planner with Visual Charts & NetworkFigure ----------------
export function Planner() {
  const { repoId } = useApp();
  const [inferred, setInferred] = React.useState(true);
  const graph = useApi<Graph>(repoId ? `/api/repositories/${repoId}/graph` : null);
  const planRes = useApi<Plan>(repoId ? `/api/repositories/${repoId}/plan?inferred=${inferred ? 1 : 0}` : null);

  if (!repoId) return <NoRepo />;

  return (
    <>
      <PageHeader
        title="Migration Planner & Dependency Bench"
        subtitle="Dependency-aware sequencing: a service is scheduled only after every service it depends on. Cycles are reported explicitly, never broken silently."
      />

      <Async res={planRes}>
        {(plan) => {
          const schedulableCount = plan.steps.filter((s) => s.status === "schedulable").length;
          const blockedCount = plan.steps.filter((s) => s.status !== "schedulable").length;

          const serviceSegments = [
            { label: "Schedulable", value: schedulableCount, color: "var(--cs-green)" },
            { label: "Blocked (Cycle)", value: blockedCount, color: "var(--cs-red)" },
          ].filter((s) => s.value > 0);

          const edgeSegments = [
            { label: "Declared Dependencies", value: plan.edgeCount.known, color: "var(--cs-blue)" },
            ...(plan.includeInferred ? [{ label: "Inferred Import Edges", value: plan.edgeCount.inferred, color: "var(--cs-accent)" }] : []),
          ];

          return (
            <>
              {plan.valid ? (
                <div className="banner banner-info">
                  Valid migration plan: <strong>{plan.waves.length} waves</strong> utilizing {plan.edgeCount.known} declared{plan.includeInferred ? ` and ${plan.edgeCount.inferred} inferred` : ""} dependencies.
                </div>
              ) : (
                <div className="banner banner-error">
                  No valid order: Cycle detected ({plan.cycles.map((c) => c.members.join(" ↔ ")).join("; ")}). Confirm or resolve an edge in the cycle.
                </div>
              )}

              {/* Visual Analytics Row */}
              <div className="grid grid-2" style={{ marginBottom: 24 }}>
                <Card title="Service Migration Readiness">
                  <DonutChart
                    segments={serviceSegments}
                    centerLabel="Services"
                    centerValue={plan.steps.length}
                  />
                </Card>

                <Card title="Interbank Dependency Graph Edges">
                  <DonutChart
                    segments={edgeSegments}
                    centerLabel="Edges"
                    centerValue={plan.edgeCount.known + (plan.includeInferred ? plan.edgeCount.inferred : 0)}
                  />
                </Card>
              </div>

              {/* Visual Wave Schedule Columns */}
              <div style={{ marginBottom: 24 }}>
                <Card title="Interactive Migration Waves Timeline">
                  <p style={{ fontSize: 13, color: "var(--cs-text-2)", marginBottom: 14 }}>
                    Each wave groups services that can safely migrate concurrently because all prerequisites are completed in prior waves.
                  </p>
                  <WaveVisualizer waves={plan.waves} cycles={plan.cycles} />
                </Card>
              </div>

              {/* Living Embedded NetworkFigure Anatomy */}
              {graph.data ? (
                <div style={{ marginBottom: 24 }}>
                  <Card
                    title="Living Banking Dependencies Bench"
                    actions={
                      <label className="kv small">
                        <input type="checkbox" checked={inferred} onChange={(e) => setInferred(e.target.checked)} />
                        Include import-inferred dependencies ({plan.edgeCount.inferred})
                      </label>
                    }
                  >
                    <p style={{ fontSize: 13, color: "var(--cs-text-2)", marginBottom: 14 }}>
                      Interactive isometric DAG bench: Selecting any service highlights its upstream prerequisites (amber conduits) and downstream dependents (blue conduits).
                    </p>
                    <NetworkFigure
                      key={`${inferred}-${plan.waves.length}`}
                      graph={graph.data}
                      plan={plan}
                    />
                  </Card>
                </div>
              ) : null}

              {/* Steps Breakdown */}
              <Card title="Service Scheduling Sequence">
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Service Node</th>
                        <th>Wave</th>
                        <th>Scheduling Status</th>
                        <th>Prerequisites</th>
                        <th>Blocked By</th>
                      </tr>
                    </thead>
                    <tbody>
                      {plan.steps.map((s) => (
                        <tr key={s.node}>
                          <td className="mono"><strong>{s.node}</strong></td>
                          <td>{s.wave ?? "—"}</td>
                          <td>
                            {s.status === "schedulable" ? (
                              <Badge tone="green">Schedulable</Badge>
                            ) : (
                              <Badge tone="red">{s.status === "blocked-cycle" ? "In cycle" : "Waiting on blocked"}</Badge>
                            )}
                          </td>
                          <td>{s.prerequisites.join(", ") || "None"}</td>
                          <td>{s.blockedBy.join(", ") || "None"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </>
          );
        }}
      </Async>
    </>
  );
}
