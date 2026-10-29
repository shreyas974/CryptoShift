#!/usr/bin/env python3
"""Build Member 3 notebooks (notebooks/member3/01..10.ipynb) in pure visual form.

All live Python computations and matplotlib figure generators reside in `src/cryptoshift/notebook_visuals.py`.
Running this script:
1. Executes all 30 visual figure generators against the real project datasets and Member 3 outputs,
   saving high-DPI PNGs to `scratch/derived/member3/figs/` and `assets/diagrams/member3/`.
2. Writes `notebooks/member3/01..10.ipynb` (and `scratch/derived/executed/01..10.ipynb`) in pure
   visual form (Markdown narrative cards + embedded PNG image attachments, zero visible code cells).
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT / "src"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from cryptoshift.notebook_visuals import REGISTRY, render_all  # noqa: E402

OUT = ROOT / "notebooks" / "member3"
EXEC_OUT = ROOT / "scratch" / "derived" / "executed"


def header(title: str, purpose: str, inputs: str, outputs: str, status: str) -> str:
    return (
        f"# {title}\n\n"
        f"**Purpose:** {purpose}\n\n"
        f"**Inputs:** {inputs}\n\n"
        f"**Visual Outputs:** {outputs}\n\n"
        f"> **Claim & Provenance Status:** {status}\n>\n"
        f"> **Scope Context:** All demo banking services in `demo_bank_app/` are **SYNTHETIC**. "
        f"High-DPI figures are also archived in `assets/diagrams/member3/` and `scratch/derived/member3/figs/`."
    )


def visual_cell(caption_title: str, caption_body: str, fig_key: str, png_path: Path) -> nbf.NotebookNode:
    b64 = base64.b64encode(png_path.read_bytes()).decode("ascii")
    fname = f"{fig_key}.png"
    md_source = (
        f"### {caption_title}\n\n"
        f"{caption_body}\n\n"
        f"![{caption_title}](attachment:{fname})"
    )
    cell = nbf.v4.new_markdown_cell(md_source)
    cell["attachments"] = {fname: {"image/png": b64}}
    return cell


VISUAL_NOTEBOOKS: Dict[str, List[Tuple]] = {
    "01_data_overview": [
        (
            "md",
            header(
                "01 — Real Datasets Visual Overview (Track C)",
                "Summarise and visualise the two real public datasets in read-only mode (Track C is descriptive only — no predictive model).",
                "`data/real/bank_tls_pqc_observations.csv` (320 rows, 5 dates) and `CESNET-TLS22-S` HDF5 (25,000,000 flows, 14 daily tables).",
                "Dataset KPI Scorecard (`01_dataset_kpis`), Longitudinal PQC Readiness Charts (`01_pqc_status_by_date`), Daily CESNET Flow Volume (`01_cesnet_rows_per_day`).",
                "VERIFIED (real public data, read-only). Public-endpoint TLS probes say nothing about a bank's internal systems or signatures; ERROR rows remain unclassified.",
            ),
        ),
        (
            "fig",
            "01A · Dataset Integrity & Volume Scorecard",
            "Read-only audit across the 320 longitudinal banking TLS 1.3 observations (64 unique hosts across 5 scan dates, 0 duplicate `(scan_file, host, ts)` keys) and out-of-core HDF5 chunk streaming over the 25.0M-flow CESNET-TLS22 S dataset.",
            "01_dataset_kpis",
        ),
        (
            "fig",
            "01B · Longitudinal Banking PQC Readiness by Scan Date",
            "Left: stacked host counts (`PQ-SAFE`, `CLASSICAL`, `ERROR`) per scan date. Right: proportional share across the 64 monitored public banking endpoints. `ERROR` probes are kept as unclassified and never relabelled as `CLASSICAL`.",
            "01_pqc_status_by_date",
        ),
        (
            "fig",
            "01C · CESNET-TLS22 S Daily Encrypted TLS Flow Volume (October 2021)",
            "Daily flow distribution across all 14 HDF5 tables (`2021-10-04` through `2021-10-17`), totalling 25,000,000 flows (mean 1.79M flows/day) used strictly for streaming scale and traffic-category demos.",
            "01_cesnet_rows_per_day",
        ),
    ],
    "02_findings_to_tasks": [
        (
            "md",
            header(
                "02 — From Cryptographic Scanner Findings to Migration Tasks",
                "Convert merged Member 2 Inventory v1.1 + legacy scanner findings into traceable per-service PQC migration tasks.",
                "`demo_bank_app/configs` (SYNTHETIC) + `demo_bank_app/services.py` via `cryptoshift.planning.planner`.",
                "Merged Findings Visual Register (`02_findings_table`), Purpose & Provenance Breakdown (`02_findings_and_evidence`), Service Task Scorecard (`02_tasks_scorecard`).",
                "VERIFIED on SYNTHETIC configs. Strict NIST FIPS 203 (`ML-KEM`) vs FIPS 204/205 (`ML-DSA`/`SLH-DSA`) role separation; `unknown` purpose forces `HOLD`.",
            ),
        ),
        (
            "fig",
            "02A · Merged Cryptographic Findings Register",
            "All 14 deduplicated findings across the demo banking estate with file/line evidence, detected legacy primitive, operation purpose, detector source, and deterministic PQC target or `HOLD` status.",
            "02_findings_table",
        ),
        (
            "fig",
            "02B · Findings by Operation Purpose & Service Evidence Provenance",
            "Left: stacked finding counts per service split by cryptographic operation purpose (`key_establishment`, `digital_signature`, `transport_protocol`, `message_digest`, `unknown`). Right: share of `OBSERVED` (scanned files) vs `DECLARED_ONLY` services.",
            "02_findings_and_evidence",
        ),
        (
            "fig",
            "02C · Per-Service Migration Task Scorecard",
            "`DECLARED_ONLY` services (`ledger_audit`, `settlement_batch`) have no scanned config files and remain on `HOLD`; `auth_gateway` also has an unattributed-purpose RSA finding held for human review.",
            "02_tasks_scorecard",
        ),
    ],
    "03_dependency_graph_and_scoring": [
        (
            "md",
            header(
                "03 — Service Dependency Graph, Provenance & Provisional Risk Scoring",
                "Visualise every upstream-to-downstream service dependency edge by provenance, highlight observed-vs-declared conflicts, and audit the additive risk formula under weight perturbations.",
                "`cryptoshift.planning` (`dependency_graph.py`, `risk.py`, `planning_config.json`).",
                "Provenance Network Graph (`03_dependency_graph`), Edge & Conflict Register (`03_edges_and_conflicts`), Risk Factor Breakdown (`03_risk_contributions`), Sensitivity Analysis (`03_sensitivity`).",
                "Graph VERIFIED on SYNTHETIC inputs (4 OBSERVED edges with file+line, 5 DECLARED edges, 0 cycles). Risk scores are PROVISIONAL and UNVALIDATED.",
            ),
        ),
        (
            "fig",
            "03A · Multi-Provenance Service Dependency Topology",
            "Directed multigraph (`upstream provider -> downstream consumer`). Teal edges (`OBSERVED`) are backed by Member 2 file+line relationship evidence (`nginx proxy_pass`, YAML `depends_on`, Python `DEPENDS_ON`); grey edges (`DECLARED`) come from the synthetic descriptor.",
            "03_dependency_graph",
        ),
        (
            "fig",
            "03B & 03C · Dependency Edge Provenance Register & Architecture Conflicts",
            "Complete register of all 9 dependency edges with file/line provenance, followed by the 3 detected discrepancies between observed configuration files and declared service metadata (e.g. `interbank_tls_nginx.conf` proxying to `ledger_audit`).",
            "03_edges_and_conflicts",
        ),
        (
            "fig",
            "03D · Provisional Risk Score Factor Contributions",
            "Additive risk score decomposition across the 5 hand-set weights (`crypto_exposure`, `network_exposure`, `criticality`, `dependents`, `verification_readiness`). Labelled `PROVISIONAL, UNVALIDATED`.",
            "03_risk_contributions",
        ),
        (
            "fig",
            "03E · One-at-a-Time Weight Perturbation Sensitivity (×0.5 / ×1.5)",
            "Across 10 perturbation runs, service risk rank order changed in 6/10 runs (minimum Kendall τ = 0.47) and the resulting wave schedule changed in 3/10 runs — demonstrating why risk weights are treated as explicit assumptions.",
            "03_sensitivity",
        ),
    ],
    "04_scheduling_opt_vs_baseline": [
        (
            "md",
            header(
                "04 — Wave Scheduling: Deterministic Exact Baseline vs QpiAI Opt MILP",
                "Schedule the 6 banking services into dependency-respecting migration waves and verify the exact 18-variable binary MILP with QpiAI Opt (`0.0.9`).",
                "Phase 2 planning problem; `cryptoshift.optimization.fallback_scheduler` and `cryptoshift.optimization.member3_qpiai`.",
                "Migration Wave Timeline & Constraint Utilisation (`04_waves`), Scheduled Tasks & QpiAI Opt Verification Scorecard (`04_schedule_and_opt_scorecard`).",
                "Baseline VERIFIED (Objective 299.1, 0 violations). QpiAI Opt offline checks (`classify=MILP`, `inspect`, `feasibility`) & owner-approved `solve(mode='local')` VERIFIED (optimal, objective 299.1 = baseline, equal assignment).",
            ),
        ),
        (
            "fig",
            "04A · Dependency-Ordered Migration Waves & Maintenance Window Utilisation",
            "Left: Gantt wave bars (`Wave 0`: `interbank_tls` + `ledger_audit`; `Wave 1`: `auth_gateway` + `payment_signing`; `Wave 2`: `card_vault` + `settlement_batch`) against the 85-minute maintenance window limit. Right: fraction of capacity (≤2 services/wave) and time (≤85 min/wave) consumed.",
            "04_waves",
        ),
        (
            "fig",
            "04B & 04C · Scheduled Tasks & QpiAI Opt MILP Comparison Scorecard",
            "Every upstream provider is scheduled no later than its downstream consumers. QpiAI Opt (`0.0.9`) classifies the 18-variable, 20-constraint model as `MILP`, confirms baseline feasibility offline, and solves `mode='local'` to the exact same optimum (`299.1`, difference `0.0`).",
            "04_schedule_and_opt_scorecard",
        ),
    ],
    "05_qcloud_simulator_experiment": [
        (
            "md",
            header(
                "05 — QpiAI Quantum / QCloud Local Statevector Simulator Experiment",
                "Reproduce the legacy `-13.07` Wave-0 QUBO energy and evaluate the Phase-2 4-qubit Wave-0 QAOA circuit on the local statevector simulator (`QpiAI-QSV-Local`).",
                "`qpiai-opt[quantum] 0.0.9`, `qpiai-quantum 0.3.0`; local device `QpiAI-QSV-Local` (1024 shots, `QAOA(reps=1)`).",
                "QAOA Simulator KPI Scorecard (`05_qaoa_scorecard`), 16-State QUBO Energy Spectrum & Sampled Shot Distribution (`05_qaoa_energy_and_samples`).",
                "SIMULATOR ONLY (`QpiAI-QSV-Local`). No QPU or cloud platform execution. Fixed-angle QAOA(reps=1) yields P(optimum) = 0.085 vs 0.0625 uniform — no quantum advantage is claimed.",
            ),
        ),
        (
            "fig",
            "05A · QAOA Reproduction & Phase-2 Wave-0 Simulator KPIs",
            "Summary metrics comparing the reproduced `-13.07` selection (`['ledger_audit', 'interbank_tls']`) and the corrected little-endian Phase-2 Wave-0 QUBO formulation (`exact optimum = -21.25`, circuit `depth=8`, `gates=18`, `1024` shots).",
            "05_qaoa_scorecard",
        ),
        (
            "fig",
            "05B · Complete 16-Bitstring QUBO Energy Landscape & QAOA Sampled Distribution",
            "Top: exact QUBO energy across all 16 4-qubit candidate subsets (teal = feasible, coral = violates capacity/window constraints). Middle: 1024-shot histogram from `QpiAI-QSV-Local` showing the true optimum `I+L (0110)` vs infeasible bitstrings. Bottom: `P(optimum) = 0.0850` vs `1/16 = 0.0625` uniform random guessing.",
            "05_qaoa_energy_and_samples",
        ),
    ],
    "06_verification_traces_and_overhead": [
        (
            "md",
            header(
                "06 — Loopback OpenSSL 3.5.9 Verification: Self-Tests, KATs, Traces, Compatibility, Overhead & Gates",
                "Execute real loopback TLS 1.3 handshakes (`X25519` vs `X25519MLKEM768` + `ML-DSA-65`), deterministic FIPS 203/204 seed KAT vectors, per-service KMS/JWS stack checks, 11-case peer compatibility matrix, and verification gates.",
                "Git-bundled OpenSSL 3.5.9 (`127.0.0.1`, throw-away keys in temp dir) and Python `cryptography 50.0.2` (`mlkem`, `mldsa`).",
                "Self-Tests, Deterministic KATs & Stack Integration (`06_selftests_kats_and_stack`), Handshake Bytes (`06_handshake_bytes`), Compatibility Matrix (`06_compatibility`), Subprocess vs In-Process Timing (`06_overhead_boxplot`), Gate Heatmap (`06_gate_heatmap`).",
                "VERIFIED, TEST SCENARIO (loopback 127.0.0.1, ephemeral test keys). 3 services reach `READY` (generic loopback evidence); 3 stay `PROPOSED` due to unresolved/held findings or missing scanned files.",
            ),
        ),
        (
            "fig",
            "06A–06C · Cryptographic Self-Tests, Deterministic Seed KAT Vectors & Service-Stack Integration",
            "OpenSSL 3.5.9 CLI and Python `cryptography` pass round-trip `ML-KEM-768` (1088 B ct, 32 B secret) and `ML-DSA-65` (3309 B sig) checks, deterministic seed KAT SHA-256 checks (`1184 B` and `1952 B` public keys), and per-service KMS DEK wrapping (`card_vault`) + JWS signing (`auth_gateway`/`payment_signing`).",
            "06_selftests_kats_and_stack",
        ),
        (
            "fig",
            "06D · Loopback TLS 1.3 Handshake Wire Bytes (Before vs After Hybrid PQC)",
            "Negotiating `X25519MLKEM768` with an EC-P256 certificate adds ~1.1 kB in each direction (`757/388 B` → `1843/1564 B`), while an `ML-DSA-65` server certificate chain increases client bytes read to `10,207 B`.",
            "06_handshake_bytes",
        ),
        (
            "fig",
            "06E · 11-Case Peer Compatibility & Negative Rejection Matrix",
            "All 11/11 loopback test cases match expected behaviour: 2 positive handshakes, 2 hybrid-to-classical fallbacks, and 7 negative cases (classical-only vs hybrid-required, TLS 1.2-only, group mismatch, expired cert, untrusted CA) cleanly rejected.",
            "06_compatibility",
        ),
        (
            "fig",
            "06F & 06G · Subprocess Handshake Wall-Clock vs Pure In-Process Primitive Timing",
            "Left: `openssl s_client` subprocess wall time (~78–96 ms) is dominated by Windows process start-up noise. Right: pure in-process Python `cryptography` microsecond benchmarks isolate the true primitive speed (`ML-KEM-768` encap+decap and `ML-DSA-65` sign+verify).",
            "06_overhead_boxplot",
        ),
        (
            "fig",
            "06H · Verification Gate Status Matrix Across All 6 Banking Services",
            "`card_vault`, `interbank_tls`, and `payment_signing` pass all required gates (`READY`). `auth_gateway` (held unknown-purpose RSA finding) and `ledger_audit` / `settlement_batch` (`DECLARED_ONLY`) fail `purpose_resolved` and remain `PROPOSED`.",
            "06_gate_heatmap",
        ),
    ],
    "07_ml_cesnet_service_class": [
        (
            "md",
            header(
                "07 — Track A: CESNET-TLS22 Service-Category Classifier (Traffic Scale Demo)",
                "Train a gradient-boosted classifier (`HistGradientBoostingClassifier`) on 210,000 streamed TLS flows split strictly by day to predict the dataset's 21 traffic service categories.",
                "CESNET-TLS22 S HDF5 (`2021-10-04..10` train [105,000 rows], `2021-10-11..17` test [105,000 rows]).",
                "Experiment Setup KPI Card (`07_cesnet_card`), Model vs Baselines (`07_metrics_vs_baselines`), Per-Class Recall (`07_per_class_recall`), Confusion Matrix (`07_confusion_matrix`).",
                "VERIFIED traffic-classification demo. **Scope boundary:** CESNET labels are traffic categories, NOT cryptographic or PQC readiness labels, and are never used for PQC detector precision/recall.",
            ),
        ),
        (
            "fig",
            "07A · Temporal Split & Streaming Sample Configuration",
            "15 evenly spaced chunks × 1,000 flows per day across 14 days (210,000 flows total), using 30 flow metadata and decoded PPI packet-direction/size/inter-packet-time features.",
            "07_cesnet_card",
        ),
        (
            "fig",
            "07B · Held-Out Test Performance vs Majority & Heuristic Baselines",
            "On held-out test days (`2021-10-11` to `2021-10-17`), `HistGradientBoosting` achieves `0.813` accuracy and `0.748` macro-F1, compared with `0.118 / 0.010` for the majority baseline and `0.246 / 0.127` for `BYTES_REV` quantile bins.",
            "07_metrics_vs_baselines",
        ),
        (
            "fig",
            "07C · Per-Class Recall Across All 21 TLS Traffic Categories",
            "High recall across major application classes (`Web`, `Mail`, `VPN`, `Cloud Storage`), with lower recall on sparse or ambiguous classes (`Virtual assistant 0.10`, `Internet Banking 0.53`).",
            "07_per_class_recall",
        ),
        (
            "fig",
            "07D · Row-Normalised 21×21 Confusion Matrix on Held-Out Days",
            "Diagonal dominance across the 21 traffic categories on unseen future days (`11–17 Oct 2021`).",
            "07_confusion_matrix",
        ),
    ],
    "08_ml_finding_purpose_triage": [
        (
            "md",
            header(
                "08 — Track B: Finding-Purpose Triage (Negative Result vs Rule Engine)",
                "Test whether a small shallow decision tree trained on public-code annotations can predict `operation_purpose` across held-out repositories better than the deterministic rule engine.",
                "`data/labels/public_code` (79 matched positive findings across 8 public repositories) evaluated with Leave-One-Repository-Out cross-validation.",
                "Pooled Metrics, Per-Repo Accuracy & Class Balance (`08_purpose_triage`), Engineering Decision Scorecard (`08_triage_decision_card`).",
                "VERIFIED negative result. The shallow tree (`Macro-F1 0.273`) loses to the deterministic rule engine (`Macro-F1 0.783`); therefore the rule engine is kept authoritative and unknown-purpose findings stay on `HOLD`.",
            ),
        ),
        (
            "fig",
            "08A · Leave-One-Repository-Out Evaluation, Per-Repo Accuracy & Purpose Balance",
            "Left: pooled LORO accuracy and macro-F1 comparing the Decision Tree (`0.646 / 0.273`), Majority Baseline (`0.658 / 0.132`), and Deterministic Rule Engine (`0.519 / 0.783`). Middle: model accuracy on each held-out repository. Right: strong class skew toward `digital_signature` and `key_establishment`.",
            "08_purpose_triage",
        ),
        (
            "fig",
            "08B · Track B Engineering Decision & Unknown-Purpose Triage Breakdown",
            "Because the small dataset (79 rows, 8 repos) is heavily skewed, the ML model fails to beat the rule engine on macro-F1. CryptoShift retains the deterministic rule engine and enforces `HOLD` whenever `operation_purpose == 'unknown'`.",
            "08_triage_decision_card",
        ),
    ],
    "09_assistant_demo": [
        (
            "md",
            header(
                "09 — CryptoShift Assistant (Read-Only Local Tools + Sarvam Cloud Back-End)",
                "Demonstrate the read-only question-answering assistant over Member 3 JSON reports, verify its 24-question safety/citation/injection benchmark, and compare `TEMPLATE_FALLBACK` with the recorded `SARVAM_CLOUD` (`sarvam-105b`) run.",
                "`scratch/derived/member3/bundle/plan.json`, `scratch/derived/member3/agent_eval.json`, and `scratch/derived/member3/agent_eval_sarvam.json`.",
                "Sample Q&A Inspection Board (`09_qa_cards`), 24-Question Evaluation Breakdown (`09_agent_eval`), Template vs Sarvam Cloud Comparison (`09_sarvam_vs_template`).",
                "TEMPLATE_FALLBACK VERIFIED (24/24). SARVAM_CLOUD (`sarvam-105b`) one owner-approved live run VERIFIED (24/24 v2 check, 18/24 stricter v3 check, ₹0.25 spend). Zero API keys read or displayed.",
            ),
        ),
        (
            "fig",
            "09A · Sample Q&A Inspection Board & Guard Outcomes",
            "Every factual answer cites exact bundle IDs (`[gate:...]`, `[edge:...]`, `[task:...]`), enforces NIST FIPS 203/204 role definitions, answers `unknown` when evidence is absent (`core_banking_mainframe`), and refuses write/approval requests.",
            "09_qa_cards",
        ),
        (
            "fig",
            "09B · Fixed 24-Question Evaluation Suite Breakdown",
            "100% pass rate (`24/24`: `cites 10/10`, `refuse 6/6`, `role 3/3`, `unknown 3/3`, `injection 2/2`) with cryptographic verification that `plan.json` and `approvals.json` remain completely unmodified after planted prompt-injection tests.",
            "09_agent_eval",
        ),
        (
            "fig",
            "09C · Deterministic Template Fallback vs Recorded Sarvam Cloud (`sarvam-105b`) Run",
            "Comparison of the offline deterministic router (`24/24`) against the recorded owner-approved `sarvam-105b` run (`24/24` on v2 check; `18/24` on stricter v3 check due to 6 over-cautious `'unknown'` answers; validator now upgraded to reject `'unknown'` when cited evidence is present).",
            "09_sarvam_vs_template",
        ),
    ],
    "10_member3_summary": [
        (
            "md",
            header(
                "10 — Member 3 Complete Visual Summary Dashboard",
                "Consolidate all verified Member 3 metrics across planning, dependency provenance, wave scheduling, QpiAI Opt & QAOA simulation, OpenSSL 3.5 verification, ML tracks, and the CryptoShift Assistant into a single executive dashboard.",
                "`scratch/derived/member3/*.json` and `reports/member3/plan.json`.",
                "6-Panel Executive Visual Dashboard (`10_dashboard`) and Complete Claim Status Scorecard (`10_summary_scorecard`).",
                "Every metric carries its explicit honesty label (`VERIFIED`, `SIMULATOR`, `PROVISIONAL`).",
            ),
        ),
        (
            "fig",
            "10A · CryptoShift Member 3 Executive Results Dashboard",
            "Six-panel visual overview covering: (1) Migration step gate states (`3 READY`, `3 PROPOSED`), (2) Optimal wave schedule (`Objective 299.1`, `0 violations`), (3) QAOA simulator sampling (`0.085` vs `0.0625` uniform), (4) Loopback TLS 1.3 handshake wire bytes, (5) ML Tracks A & B Macro-F1, and (6) Assistant evaluation (`24/24`).",
            "10_dashboard",
        ),
        (
            "fig",
            "10B · Complete Member 3 Deliverable & Claim Status Scorecard",
            "End-to-end summary table pairing each measured result with its verified scope and claim status label.",
            "10_summary_scorecard",
        ),
    ],
}


def build(only: List[str] | None = None) -> List[Path]:
    """Render all PNG figures and write visual-only notebooks to notebooks/member3/ and scratch/derived/executed/."""
    OUT.mkdir(parents=True, exist_ok=True)
    EXEC_OUT.mkdir(parents=True, exist_ok=True)
    prefixes = [o[:2] for o in only] if only else None
    rendered = render_all(prefixes)
    written: List[Path] = []

    for name, items in VISUAL_NOTEBOOKS.items():
        if only and not any(name.startswith(o) for o in only):
            continue
        nb = nbf.v4.new_notebook()
        nb.metadata["kernelspec"] = {
            "name": "cryptoshift-m3",
            "display_name": "CryptoShift M3 (.venv)",
            "language": "python",
        }
        cells = []
        for item in items:
            kind = item[0]
            if kind == "md":
                cells.append(nbf.v4.new_markdown_cell(item[1]))
            elif kind == "fig":
                _, cap_title, cap_body, fig_key = item
                png_path = rendered.get(fig_key) or REGISTRY[fig_key]()
                cells.append(visual_cell(cap_title, cap_body, fig_key, png_path))
        nb.cells = cells
        path = OUT / f"{name}.ipynb"
        exec_path = EXEC_OUT / f"{name}.ipynb"
        nbf.write(nb, path)
        nbf.write(nb, exec_path)
        written.append(path)
    return written


if __name__ == "__main__":
    for p in build(sys.argv[1:] or None):
        print(p.relative_to(ROOT).as_posix())
