"""Migration proposal generator for banking services transitioning to Hybrid Post-Quantum Cryptography."""

from __future__ import annotations

from typing import Any, Dict, List

from cryptoshift.models import MigrationTask


def generate_migration_proposals(tasks: List[MigrationTask], task_to_wave: Dict[str, int]) -> List[Dict[str, Any]]:
    """Generate concrete hybrid PQC migration proposals annotated with wave assignments."""
    proposals: List[Dict[str, Any]] = []
    for task in tasks:
        wave = task_to_wave.get(task.service_id, -1)
        proposals.append(
            {
                "service_id": task.service_id,
                "service_name": task.name,
                "assigned_wave": wave,
                "legacy_primitives": task.legacy_algorithms,
                "proposed_pqc_primitives": task.target_algorithms,
                "migration_mode": "Hybrid Dual-Mode (Classical + NIST FIPS 203/204)",
                "dependencies": task.dependencies,
                "verification_gate_required": True,
                "rollback_snapshot_policy": "Automatic pre-wave key & cipher state snapshot",
            }
        )
    return sorted(proposals, key=lambda item: (item["assigned_wave"], item["service_id"]))
