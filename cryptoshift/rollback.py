"""Automated cryptographic state snapshot and rollback manager when verification gates fail."""

from __future__ import annotations

from typing import Dict, List

from cryptoshift.models import MigrationTask, RollbackEvent, VerificationGateResult


def evaluate_rollbacks(
    tasks: List[MigrationTask],
    gate_results: List[VerificationGateResult],
) -> List[RollbackEvent]:
    """Create rollback events for any service whose verification gate failed."""
    task_map: Dict[str, MigrationTask] = {t.service_id: t for t in tasks}
    events: List[RollbackEvent] = []
    for idx, gate in enumerate(gate_results, start=1):
        task = task_map[gate.service_id]
        restored = ", ".join(task.legacy_algorithms)
        if not gate.overall_passed:
            events.append(
                RollbackEvent(
                    service_id=gate.service_id,
                    wave_index=gate.wave_index,
                    triggered=True,
                    reason=gate.details,
                    restored_algorithm=restored,
                    snapshot_id=f"SNAP-W{gate.wave_index}-{idx:02d}",
                )
            )
        else:
            events.append(
                RollbackEvent(
                    service_id=gate.service_id,
                    wave_index=gate.wave_index,
                    triggered=False,
                    reason="Verification gate passed; hybrid PQC configuration committed.",
                    restored_algorithm="N/A (Committed Hybrid PQC)",
                    snapshot_id=f"SNAP-W{gate.wave_index}-{idx:02d}",
                )
            )
    return events
