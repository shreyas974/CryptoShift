"""Migration readiness and solver comparison metrics for CryptoShift."""

from __future__ import annotations

from typing import Any, Dict, List

from cryptoshift.models import CryptoFinding, MigrationTask, VerificationGateResult, WaveScheduleResult


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
