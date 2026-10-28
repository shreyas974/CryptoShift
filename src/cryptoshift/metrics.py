"""Migration readiness, solver comparison, and labelled dataset evaluation metrics for CryptoShift."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from cryptoshift.models import CryptoFinding, MigrationTask, VerificationGateResult, WaveScheduleResult
from cryptoshift.scanner import scan_source_file


def compute_migration_metrics(
    findings: List[CryptoFinding],
    tasks: List[MigrationTask],
    schedule: WaveScheduleResult,
    gates: List[VerificationGateResult],
) -> Dict[str, Any]:
    """Compute summary metrics across discovery, scheduling, and verification gates."""
    shor_vulnerable = sum(1 for f in findings if "Shor" in f.quantum_threat)
    passed_gates = sum(1 for g in gates if g.overall_passed)
    return {
        "total_services": len(tasks),
        "total_crypto_findings": len(findings),
        "shor_vulnerable_findings": shor_vulnerable,
        "grover_weakened_findings": len(findings) - shor_vulnerable,
        "schedule_solver": schedule.solver_name,
        "schedule_status": schedule.status,
        "schedule_feasible": schedule.feasible,
        "schedule_objective": schedule.objective_value,
        "waves_used": len([w for w, svcs in schedule.waves.items() if svcs]),
        "verification_gates_passed": passed_gates,
        "verification_gates_total": len(gates),
    }


def evaluate_labelled_dataset(project_root: Path) -> Dict[str, Any]:
    """Evaluate `scan_source_file` on the documented synthetic fixture dataset with repository-level splits.

    Unit of analysis: One labelled fixture file instance in `data/labels/synthetic_fixture_labels.json`,
    evaluated on whether the detector identifies both the presence of a migration-relevant cryptographic
    operation and its correct `operation_purpose` (`key_establishment`, `digital_signature`, etc.).
    """
    labels_path = project_root / "data" / "labels" / "synthetic_fixture_labels.json"
    pub_refs_path = project_root / "data" / "labels" / "public_repo_references.json"

    if not labels_path.is_file():
        return {"status": "blocked (missing data/labels/synthetic_fixture_labels.json)"}

    label_bundle = json.loads(labels_path.read_text(encoding="utf-8"))
    instances: List[Dict[str, Any]] = label_bundle.get("instances", [])
    pub_refs = (
        json.loads(pub_refs_path.read_text(encoding="utf-8"))
        if pub_refs_path.is_file()
        else {"repositories": []}
    )

    tp = 0
    fp = 0
    fn = 0
    tn = 0
    split_counts: Dict[str, Dict[str, int]] = {}
    instance_outcomes: List[Dict[str, Any]] = []

    for item in instances:
        rel_path = item["relative_path"]
        split = item["repository_split"]
        expected_positive = bool(item["has_migration_relevant_crypto"])
        expected_alg = item.get("expected_algorithm")
        expected_purpose = item.get("expected_purpose")

        if split not in split_counts:
            split_counts[split] = {"TP": 0, "FP": 0, "FN": 0, "TN": 0}

        full_path = project_root / rel_path
        detected = scan_source_file(full_path, service_id=item["repository_id"])

        if expected_positive:
            matched = any(
                d.legacy_algorithm == expected_alg and d.operation_purpose == expected_purpose
                for d in detected
            )
            if matched:
                tp += 1
                split_counts[split]["TP"] += 1
                verdict = "TP"
            else:
                fn += 1
                split_counts[split]["FN"] += 1
                verdict = "FN"
        else:
            if len(detected) == 0:
                tn += 1
                split_counts[split]["TN"] += 1
                verdict = "TN"
            else:
                fp += 1
                split_counts[split]["FP"] += 1
                verdict = "FP"

        instance_outcomes.append(
            {
                "instance_id": item["instance_id"],
                "repository_id": item["repository_id"],
                "repository_split": split,
                "relative_path": rel_path,
                "expected_positive": expected_positive,
                "expected_algorithm": expected_alg,
                "expected_purpose": expected_purpose,
                "detected_count": len(detected),
                "detected_items": [
                    {
                        "algorithm": d.legacy_algorithm,
                        "purpose": d.operation_purpose,
                        "line": d.line_number,
                        "confidence": d.confidence,
                    }
                    for d in detected
                ],
                "verdict": verdict,
                "notes": item.get("notes", ""),
            }
        )

    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0

    return {
        "dataset_classification": "SYNTHETIC_FIXTURE_EVALUATION (Visibly separated in data/fixtures/synthetic/; NOT real-world banking data)",
        "unit_of_analysis": "One labelled file-level cryptographic operation instance (requiring both algorithm clue and operation_purpose match for TP).",
        "split_method": "Repository-level split across 3 synthetic mini-projects (calibration: project_alpha_auth; held_out_test: project_beta_tls, project_gamma_noncrypto).",
        "total_instances": len(instances),
        "counts": {
            "TP": tp,
            "FP": fp,
            "FN": fn,
            "TN": tn,
        },
        "metrics": {
            "precision": precision,
            "recall": recall,
        },
        "by_split": split_counts,
        "instance_outcomes": instance_outcomes,
        "public_repository_references_count": len(pub_refs.get("repositories", [])),
        "limitations": [
            "These precision and recall counts are measured on a small, controlled synthetic fixture suite (data/fixtures/synthetic/) to verify detector logic and error modes (such as dynamic reflection FN and ambiguous config FP).",
            "Synthetic fixture scores do NOT represent detection performance on real-world production banking estates.",
            "Public open-source repository references in data/labels/public_repo_references.json are pinned by URL and commit SHA for reproducible external evaluation without redistributing third-party source trees.",
        ],
    }

