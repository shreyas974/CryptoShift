"""Member 3 isolated migration planning, risk breakdown, QpiAI optimization, verification, and rollback analysis.

Consumes the unmodified shared `src/cryptoshift/` interfaces and writes derived outputs strictly under
`member3/outputs/` and `member3/reports/`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

MEMBER3_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MEMBER3_ROOT.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cryptoshift.dependencies import build_dependency_edges, validate_dependency_order  # noqa: E402
from cryptoshift.models import MigrationTask, WaveScheduleConfig  # noqa: E402
from cryptoshift.optimization.fallback_scheduler import solve_with_fallback_scheduler  # noqa: E402
from cryptoshift.optimization.qcloud_experiment import run_qcloud_wave0_qubo_experiment  # noqa: E402
from cryptoshift.optimization.qpiai_opt_adapter import solve_with_qpiai_opt  # noqa: E402
from cryptoshift.proposals import generate_migration_proposals  # noqa: E402
from cryptoshift.protocol_demo import run_hybrid_protocol_demo  # noqa: E402
from cryptoshift.rollback import evaluate_rollbacks  # noqa: E402
from cryptoshift.rules import resolve_contextual_pqc_rule  # noqa: E402
from cryptoshift.scanner import scan_banking_services  # noqa: E402
from cryptoshift.scoring import (  # noqa: E402
    ALGORITHM_BASE_RISK,
    CRITICALITY_MULTIPLIER,
    build_migration_tasks,
    compute_service_risk,
)
from cryptoshift.verification import run_verification_gates  # noqa: E402
from demo_bank_app.services import SYNTHETIC_BANK_SERVICES  # noqa: E402


def build_explainable_risk_table(tasks: Optional[List[MigrationTask]] = None) -> List[Dict[str, Any]]:
    """Compute a transparent, explainable breakdown of Member 3's service risk scoring formula."""
    task_list = tasks if tasks is not None else build_migration_tasks()
    rows: List[Dict[str, Any]] = []
    for task in task_list:
        meta = SYNTHETIC_BANK_SERVICES.get(task.service_id, {})
        retention_years = int(meta.get("data_retention_years", 10))
        alg_scores = {a: ALGORITHM_BASE_RISK.get(a, 3.0) for a in task.legacy_algorithms}
        mean_alg = sum(alg_scores.values()) / max(len(alg_scores), 1)
        mult = CRITICALITY_MULTIPLIER.get(task.criticality, 1.0)
        retention_bonus = min(retention_years / 10.0, 1.5)
        score = compute_service_risk(task.legacy_algorithms, task.criticality, retention_years)

        role_mappings = []
        for t_alg in task.target_algorithms:
            if "ML-KEM" in t_alg or "MLKEM" in t_alg:
                role_mappings.append("key_establishment -> FIPS 203 ML-KEM")
            elif "ML-DSA" in t_alg or "SLH-DSA" in t_alg:
                role_mappings.append("digital_signature -> FIPS 204 ML-DSA")
            elif "AES-256-GCM" in t_alg:
                role_mappings.append("symmetric_encryption -> NIST SP 800-38D AES-256-GCM")
            elif "SHA3" in t_alg:
                role_mappings.append("message_digest -> FIPS 202 SHA-3")

        rows.append(
            {
                "service_id": task.service_id,
                "service_name": task.name,
                "owner": task.owner,
                "criticality": task.criticality,
                "legacy_algorithms": task.legacy_algorithms,
                "target_algorithms": task.target_algorithms,
                "nist_role_mappings": role_mappings,
                "mean_algorithm_base_risk": round(mean_alg, 3),
                "criticality_multiplier": mult,
                "data_retention_years": retention_years,
                "hndl_retention_bonus": round(retention_bonus, 3),
                "risk_score": score,
                "dependencies": task.dependencies,
                "verification_ready_wave0": task.verification_ready_wave0,
            }
        )
    return sorted(rows, key=lambda r: r["risk_score"], reverse=True)


def run_member3_planning_and_verification_analysis(
    simulate_failure_service: Optional[str] = None,
) -> Dict[str, Any]:
    """Run Member 3's complete planning, QpiAI offline IR/simulator check, verification gates, and rollback analysis."""
    findings = scan_banking_services()
    tasks = build_migration_tasks()
    cfg = WaveScheduleConfig()

    risk_table = build_explainable_risk_table(tasks)
    dep_edges = build_dependency_edges(tasks)
    fallback_schedule = solve_with_fallback_scheduler(tasks, cfg)
    dep_ok, dep_violations = validate_dependency_order(tasks, fallback_schedule.task_to_wave)

    opt_schedule, opt_meta = solve_with_qpiai_opt(tasks, cfg, allow_online_auth=False)
    qcloud_meta = run_qcloud_wave0_qubo_experiment(allow_online_auth=False)

    proposals = generate_migration_proposals(tasks, fallback_schedule.task_to_wave)
    nominal_gates = run_verification_gates(tasks, fallback_schedule.task_to_wave, findings=findings)
    nominal_rollbacks = evaluate_rollbacks(tasks, nominal_gates)

    failure_target = simulate_failure_service or "interbank_tls"
    simulated_fail_gates = run_verification_gates(
        tasks,
        fallback_schedule.task_to_wave,
        findings=findings,
        simulate_failure_service=failure_target,
    )
    simulated_fail_rollbacks = evaluate_rollbacks(tasks, simulated_fail_gates)
    protocol_trace = run_hybrid_protocol_demo()

    # Verify strict NIST PQC role separation
    rsa_sig = resolve_contextual_pqc_rule("RSA-2048", "digital_signature")
    rsa_kem = resolve_contextual_pqc_rule("RSA-2048", "key_establishment")
    rsa_unk = resolve_contextual_pqc_rule("RSA-2048", "unknown")

    result = {
        "nist_role_separation_check": {
            "RSA-2048_digital_signature": rsa_sig,
            "RSA-2048_key_establishment": rsa_kem,
            "RSA-2048_unknown_purpose": rsa_unk,
        },
        "explainable_risk_table": risk_table,
        "dependency_edges": [{"upstream": u, "downstream": v} for u, v in dep_edges],
        "dependency_order_valid": dep_ok,
        "dependency_violations": dep_violations,
        "deterministic_fallback_schedule": fallback_schedule.to_dict(),
        "qpiai_opt_offline_check": opt_meta,
        "qpiai_qcloud_wave0_qubo_simulator": qcloud_meta,
        "migration_proposals": proposals,
        "nominal_verification_gates": [g.to_dict() for g in nominal_gates],
        "nominal_rollback_events": [r.to_dict() for r in nominal_rollbacks],
        "simulated_failure_experiment": {
            "simulated_failure_service": failure_target,
            "gates": [g.to_dict() for g in simulated_fail_gates],
            "rollback_events": [r.to_dict() for r in simulated_fail_rollbacks],
        },
        "protocol_overhead_trace": protocol_trace,
    }

    outputs_dir = MEMBER3_ROOT / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    (outputs_dir / "planning_verification_bundle.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    return result
