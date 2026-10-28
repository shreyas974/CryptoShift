"""Non-sensitive JSON and Markdown evidence reporting for CryptoShift QpiAI and dataset evaluation runs."""

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

