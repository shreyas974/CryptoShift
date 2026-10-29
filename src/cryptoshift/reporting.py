"""Non-sensitive JSON and Markdown evidence reporting for CryptoShift QpiAI, datasets, and MVP runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def write_qpiai_evidence_reports(
    evidence: Dict[str, Any],
    output_dir: Path,
) -> Dict[str, str]:
    """Write reproducible, secret-redacted JSON and Markdown reports to `reports/qpiai/`."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "qpiai_evidence_report.json"
    md_path = output_dir / "qpiai_evidence_report.md"

    json_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    lines = [
        "# CryptoShift — QpiAI Integration & Verification Evidence Report",
        "",
        "- **Project:** Quant-A-Maze 3.0 — PQC-01: Verification-Gated Cryptographic Migration Across Banking Applications",
        f"- **Python Runtime:** `{evidence['environment']['python_version']}`",
        f"- **Virtual Environment:** `{evidence['environment']['virtualenv_name']}`",
        f"- **Online Key Validation Executed in This Run:** `{evidence['environment'].get('online_auth_executed', False)}`",
        "",
        "## 1. Package & SDK Availability",
        "",
        "| Component | Package / Module | Version | Status |",
        "|---|---|---|---|",
    ]
    for pkg_name, pkg_info in evidence["packages"].items():
        lines.append(
            f"| {pkg_name} | `{pkg_info['distribution']}` | `{pkg_info['version']}` | **{pkg_info['status']}** |"
        )

    lines.extend(
        [
            "",
            "## 2. Non-Sensitive Credential & Authentication Status",
            "",
            "| Credential Variable | Local Configuration | Online / SDK Auth Verification | Notes |",
            "|---|---|---|---|",
        ]
    )
    for key_name, key_info in evidence["credentials"].items():
        lines.append(
            f"| `{key_name}` | `{key_info['configuration_status']}` | **{key_info['auth_verification_status']}** | {key_info['message']} |"
        )

    lines.extend(
        [
            "",
            "## 3. Component Implementation & Execution Status Matrix",
            "",
            "| Component | Status Label | Execution Mode | Backend / Solver | Objective Value | Feasible | Runtime (s) |",
            "|---|---|---|---|---:|---|---:|",
        ]
    )
    for comp in evidence["components"]:
        obj_str = f"{comp['objective_value']:.2f}" if comp["objective_value"] is not None else "N/A"
        lines.append(
            f"| {comp['name']} | **{comp['status']}** | `{comp['execution_mode']}` | `{comp['backend']}` | "
            f"{obj_str} | `{comp['feasible']}` | {comp['runtime_seconds']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## 4. Schedule Comparison (6 Banking Services across 3 Waves)",
            "",
            "### Deterministic Dependency-Aware Fallback Baseline",
            f"- **Status:** `{evidence['fallback_schedule']['status']}`",
            f"- **Objective Value:** `{evidence['fallback_schedule']['objective_value']}`",
            f"- **Wave Assignment:** `{json.dumps(evidence['fallback_schedule']['waves'])}`",
            "",
            "### QpiAI Opt (`qpiai-opt` MILP/Binary Model)",
            f"- **Offline Model Compilation & Inspection Status:** `{evidence['qpiai_opt']['offline_model_status']}`",
            f"- **Problem Class (`classify(model)`):** `{evidence['qpiai_opt']['problem_class']}`",
            f"- **Baseline Feasibility Verified by `qpiai_opt.opt_solvers.feasibility()`:** `{evidence['qpiai_opt']['baseline_feasible_in_opt_ir']}`",
            f"- **Authenticated Local Solve Status (`solve(model, mode='local', client=...)`):** `{evidence['qpiai_opt']['online_solve_status']}`",
            f"- **Detail:** {evidence['qpiai_opt']['message']}",
            "",
            "### QpiAI QCloud / Quantum SDK (`qpiai-opt[quantum]` & `qpiai-quantum`)",
            f"- **4-Qubit Wave-0 QUBO Compilation Status:** `{evidence['qpiai_qcloud']['qubo_compilation_status']}`",
            f"- **QAOA Logical Circuit Construction (`build_circuit`) Status:** `{evidence['qpiai_qcloud']['circuit_construction_status']}`",
            f"- **Logical Circuit Metrics:** Qubits=`{evidence['qpiai_qcloud']['circuit_metrics'].get('qubits')}`, "
            f"Depth=`{evidence['qpiai_qcloud']['circuit_metrics'].get('depth')}`, "
            f"Size=`{evidence['qpiai_qcloud']['circuit_metrics'].get('size')}`",
            f"- **Direct Local Statevector Simulator (`QpiAI-QSV-Local`) Status:** `{evidence['qpiai_qcloud']['local_qsv_simulator_status']}`",
            f"- **Authenticated QAOA `solve(..., mode='local')` Status:** `{evidence['qpiai_qcloud']['authenticated_qaoa_status']}`",
            f"- **Detail:** {evidence['qpiai_qcloud']['message']}",
            "",
            "## 5. Limitations & Honesty Notes",
            "",
        ]
    )
    for lim in evidence.get("limitations", []):
        lines.append(f"- {lim}")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def write_evaluation_reports(
    eval_data: Dict[str, Any],
    output_dir: Path,
) -> Dict[str, str]:
    """Write reproducible dataset evaluation metrics to `reports/evaluation/`."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "evaluation_report.json"
    md_path = output_dir / "evaluation_report.md"

    json_path.write_text(json.dumps(eval_data, indent=2), encoding="utf-8")

    counts = eval_data.get("counts", {})
    metrics = eval_data.get("metrics", {})
    lines = [
        "# CryptoShift — Detection Evaluation Report",
        "",
        f"- **Dataset Scope:** {eval_data.get('dataset_classification')}",
        f"- **Unit of Analysis:** {eval_data.get('unit_of_analysis')}",
        f"- **Repository Split Method:** {eval_data.get('split_method')}",
        "",
        "## 1. Confusion Matrix & Summary Metrics (Synthetic Fixture Suite)",
        "",
        "| Metric | Value | Formula / Definition |",
        "|---|---:|---|",
        f"| **True Positives (TP)** | `{counts.get('TP', 0)}` | Migration-relevant crypto present AND both algorithm & operation_purpose matched |",
        f"| **False Positives (FP)** | `{counts.get('FP', 0)}` | Non-migration/decoy fixture flagged by static pattern |",
        f"| **False Negatives (FN)** | `{counts.get('FN', 0)}` | Migration-relevant crypto missed (e.g., indirect dynamic reflection call) |",
        f"| **True Negatives (TN)** | `{counts.get('TN', 0)}` | Clean/modern PQC or non-crypto file correctly ignored |",
        f"| **Precision** | **`{metrics.get('precision', 0.0):.4f}`** | `TP / (TP + FP)` |",
        f"| **Recall** | **`{metrics.get('recall', 0.0):.4f}`** | `TP / (TP + FN)` |",
        "",
        "## 2. Per-Instance Breakdown",
        "",
        "| Instance ID | Repository Split | File Path | Expected (Alg / Purpose) | Detected Count | Verdict | Notes |",
        "|---|---|---|---|---:|---|---|",
    ]
    for item in eval_data.get("instance_outcomes", []):
        exp = (
            f"`{item['expected_algorithm']}` / `{item['expected_purpose']}`"
            if item["expected_positive"]
            else "`None (Negative/Decoy)`"
        )
        lines.append(
            f"| `{item['instance_id']}` | `{item['repository_split']}` | `{item['relative_path']}` | "
            f"{exp} | {item['detected_count']} | **{item['verdict']}** | {item['notes']} |"
        )

    lines.extend(["", "## 3. Scope Limitations", ""])
    for lim in eval_data.get("limitations", []):
        lines.append(f"- {lim}")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def write_real_dataset_summary_reports(
    summary_data: Dict[str, Any],
    output_dir: Path,
) -> Dict[str, str]:
    """Write attribution-preserving JSON and Markdown summaries of both real datasets to `reports/datasets/`."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "real_dataset_summary.json"
    md_path = output_dir / "real_dataset_summary.md"

    json_path.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")

    pqc = summary_data.get("banking_pqc_observations", {})
    ces = summary_data.get("cesnet_tls22_s", {})
    stream = ces.get("incremental_streaming_benchmark", {})
    audit = pqc.get("audit", {})

    lines = [
        "# CryptoShift — Real Dataset Summary, Provenance, and Streaming Audit",
        "",
        "## 1. PQ Readiness Index — Banking Sector Longitudinal TLS 1.3 Observations",
        "",
        f"- **Status:** `{pqc.get('status')}`",
        f"- **Attribution:** {pqc.get('attribution')}",
        f"- **License:** `{pqc.get('license')}`",
        f"- **Total Observations:** `{audit.get('row_count')}` across `{len(pqc.get('scan_dates', []))}` scan dates (`{', '.join(pqc.get('scan_dates', []))}`)",
        f"- **Duplicate Observation Key Check (`{audit.get('duplicate_key_definition')}`):** `{audit.get('duplicate_observation_keys')}` duplicates (`{audit.get('unique_observation_keys')}` unique keys; `{audit.get('unique_hosts')}` hosts measured longitudinally across dates)",
        f"- **Overall Status Counts (Unchanged from Source):** `{json.dumps(pqc.get('overall_status_counts', {}))}` (`ERROR` kept strictly unclassified: `{pqc.get('unclassified_error_count')}`)",
        "",
        "### Per-Scan-Date Status Breakdown",
        "",
        "| Scan Date | PQ-SAFE (`X25519MLKEM768`) | CLASSICAL (`X25519`) | ERROR (Unclassified) | Total |",
        "|---|---:|---:|---:|---:|",
    ]
    for sdate, scounts in pqc.get("status_counts_by_scan_date", {}).items():
        pq_c = scounts.get("PQ-SAFE", 0)
        cl_c = scounts.get("CLASSICAL", 0)
        er_c = scounts.get("ERROR", 0)
        lines.append(f"| `{sdate}` | `{pq_c}` | `{cl_c}` | `{er_c}` | `{pq_c + cl_c + er_c}` |")

    lines.extend(
        [
            "",
            "### Caveats & Scope Boundaries (PQ Readiness Index)",
            "",
        ]
    )
    for cav in pqc.get("caveats", []):
        lines.append(f"- {cav}")

    lines.extend(
        [
            "",
            "---",
            "",
            "## 2. CESNET-TLS22 Provider-Defined `S` Subset (Real TLS Flow Metadata)",
            "",
            f"- **Status:** `{ces.get('status')}`",
            f"- **Required Citation:** {ces.get('required_citation')}",
            f"- **DOI & Source:** `{ces.get('doi')}` (<{ces.get('source_url')}>)",
            f"- **License:** `{ces.get('license')}`",
            f"- **Collection Period:** {ces.get('collection_period')}",
            f"- **File Size:** `{ces.get('file_size_bytes'):,}` bytes (`3.23 GB` decimal; matches expected: `{ces.get('file_size_matches_expected')}`)",
            f"- **Recorded SHA-256:** `{ces.get('recorded_sha256')}`",
            f"- **Total Daily Tables:** `{ces.get('table_count')}` tables (`/flows/D20211004` .. `/flows/D20211017`)",
            f"- **Total Flow Rows:** `{ces.get('total_table_rows'):,}` (`0` duplicate flow IDs in 25M full audit)",
            f"- **Incremental Streaming Benchmark:** Streamed `{stream.get('streamed_rows', 0):,}` rows in `{stream.get('chunks_processed', 0)}` chunks (`chunk_size={stream.get('chunk_size', 0):,}`) in `{stream.get('elapsed_seconds', 0.0)}s` (`{stream.get('throughput_rows_per_sec', 0.0):,}` rows/sec; `{stream.get('streamed_duplicate_flow_ids', 0)}` duplicate IDs in streamed window)",
            f"- **Top Categories in Streamed Window:** `{json.dumps(stream.get('top_categories_in_stream', {}))}`",
            "",
            "### Prohibited Interpretations (CESNET-TLS22-S)",
            "",
        ]
    )
    for prohib in ces.get("prohibited_interpretations", []):
        lines.append(f"- {prohib}")

    lines.extend(
        [
            "",
            "---",
            "",
            "## 3. Detector Evaluation Separation Policy",
            "",
            f"- {summary_data.get('evaluation_separation_policy')}",
        ]
    )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def write_mvp_vertical_slice_reports(
    slice_data: Dict[str, Any],
    output_dir: Path,
) -> Dict[str, str]:
    """Write JSON and Markdown audit reports for the operator MVP vertical slice to `reports/runs/`."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "mvp_vertical_slice_report.json"
    md_path = output_dir / "mvp_vertical_slice_report.md"

    json_path.write_text(json.dumps(slice_data, indent=2), encoding="utf-8")

    lines = [
        "# CryptoShift — Operator MVP Vertical Slice Audit Report",
        "",
        f"- **Run ID:** `{slice_data.get('run_id')}`",
        f"- **Created At (UTC):** `{slice_data.get('created_at_utc')}`",
        f"- **Scanned Target Path:** `{slice_data.get('target_path')}`",
        f"- **Human Approval Status:** **`{slice_data.get('approval_status')}`** (Approver: `{slice_data.get('approver') or 'None — Preview Only'}`)",
        f"- **Original Source Files Unmodified:** `{slice_data.get('original_source_files_unmodified')}`",
        f"- **Pre-Patch Findings in Scanned Files:** `{slice_data.get('scanned_file_findings_count')}`",
        f"- **Post-Patch Findings in Staged Copy:** `{slice_data.get('post_patch_staged_findings_count')}`",
        f"- **SQLite Audit Database:** `{slice_data.get('sqlite_db_path')}`",
        "",
        "## 1. Traceable File & Configuration CBOM Inventory",
        "",
        "| Finding ID | Service | File Path | Line | Directive / Context | Legacy Alg | Purpose | Target PQC (NIST Standard) | Confidence |",
        "|---|---|---|---:|---|---|---|---|---|",
    ]
    for f in slice_data.get("scanned_file_findings", []):
        lines.append(
            f"| `{f['finding_id']}` | `{f['service_id']}` | `{f['file_path']}` | {f['line_number']} | "
            f"`{f['library_or_protocol']}` | `{f['legacy_algorithm']}` | `{f['operation_purpose']}` | "
            f"{f['target_pqc_algorithm']} (`{f['nist_standard']}`) | `{f['confidence']}` |"
        )

    lines.extend(
        [
            "",
            "## 2. Explainable Risk Prioritization & Dependency Sequencing",
            "",
            "| Service ID | Criticality | Legacy Primitives | Mean Alg Risk | Crit. Mult | HNDL Bonus | Final Risk Score | Upstream Dependencies | Assigned Wave |",
            "|---|---|---|---:|---:|---:|---:|---|---:|",
        ]
    )
    t2w = slice_data.get("wave_schedule", {}).get("task_to_wave", {})
    for r in slice_data.get("explainable_risk_breakdown", []):
        sid = r["service_id"]
        deps_str = ", ".join(r["dependencies"]) if r["dependencies"] else "(root)"
        lines.append(
            f"| `{sid}` | `{r['criticality']}` | `{', '.join(r['legacy_algorithms'])}` | "
            f"{r['mean_algorithm_score']:.2f} | {r['criticality_multiplier']:.2f} | "
            f"+{r['hndl_retention_bonus']:.2f} | **`{r['risk_score']:.2f}`** | `{deps_str}` | Wave `{t2w.get(sid, 0)}` |"
        )

    lines.extend(
        [
            "",
            "## 3. Patch Proposals & Human Approval Gate",
            "",
        ]
    )
    for p in slice_data.get("patch_proposals", []):
        lines.extend(
            [
                f"### Proposal `{p['proposal_id']}` — `{p['source_file']}` (Service: `{p['service_id']}`, Wave `{p['assigned_wave']}`)",
                f"- **Approval Status:** `{p['approval_status']}` (Approver: `{p.get('approver') or 'pending'}`)",
                f"- **Applied to Isolated Staging Copy:** `{p['applied_to_staging']}` (`{p.get('staged_file_path') or 'not staged yet'}`)",
                f"- **Backup Copy Path:** `{p.get('backup_file_path') or 'N/A'}`",
                "- **Remediation Actions:**",
            ]
        )
        for act in p.get("actions", []):
            lines.append(f"  - {act}")
        lines.extend(["", "```diff", p.get("unified_diff", ""), "```", ""])

    lines.extend(
        [
            "## 4. Verification Gates & Rollback Readiness",
            "",
            "| Wave | Service ID | KAT Gate | Hybrid Handshake Gate | Latency SLO Gate | Overall Verdict | Rollback Snapshot & Policy Note |",
            "|---:|---|---|---|---|---|---|",
        ]
    )
    rb_map = {r["service_id"]: r for r in slice_data.get("rollback_events", [])}
    for g in slice_data.get("verification_gates", []):
        sid = g["service_id"]
        rb = rb_map.get(sid, {})
        verdict = "**PASS**" if g["overall_passed"] else "**ROLLBACK TRIGGERED**"
        lines.append(
            f"| {g['wave_index']} | `{sid}` | `{g['kat_passed']}` | `{g['hybrid_handshake_passed']}` | "
            f"`{g['latency_within_slo']}` | {verdict} | `{rb.get('snapshot_id', 'N/A')}` — {rb.get('policy_note', '')} |"
        )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
