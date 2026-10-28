"""Automated cryptographic state snapshot and rollback manager when verification gates fail."""

from __future__ import annotations

from typing import Dict, List

from cryptoshift.models import MigrationTask, RollbackEvent, VerificationGateResult


def evaluate_rollbacks(
    tasks: List[MigrationTask],
    gate_results: List[VerificationGateResult],
) -> List[RollbackEvent]:
    """Create rollback records with feature flags, owners, stop triggers, and policy warnings."""
    task_map: Dict[str, MigrationTask] = {t.service_id: t for t in tasks}
    events: List[RollbackEvent] = []
    for idx, gate in enumerate(gate_results, start=1):
        task = task_map[gate.service_id]
        restored = ", ".join(task.legacy_algorithms)
        has_deprecated = any(alg in ("SHA-1", "3DES") for alg in task.legacy_algorithms)
        policy_note = (
            "POLICY WARNING: Reverting to SHA-1 or 3DES violates NIST SP 800-131A; fallback must use classical SHA-256/AES-256-GCM baseline instead of weak legacy cipher."
            if has_deprecated
            else "Classical RSA-2048/ECDSA-P256 fallback permitted temporarily under dual-mode transition policy."
        )
        if not gate.overall_passed:
            events.append(
                RollbackEvent(
                    service_id=gate.service_id,
                    wave_index=gate.wave_index,
                    triggered=True,
                    reason=gate.details,
                    restored_algorithm=restored,
                    snapshot_id=f"SNAP-W{gate.wave_index}-{idx:02d}",
                    owner=task.owner,
                    policy_note=policy_note,
                )
            )
        else:
            events.append(
                RollbackEvent(
                    service_id=gate.service_id,
                    wave_index=gate.wave_index,
                    triggered=False,
                    reason="Verification gate passed; hybrid PQC configuration ready for human promotion.",
                    restored_algorithm="N/A (Standby Snapshot Ready)",
                    snapshot_id=f"SNAP-W{gate.wave_index}-{idx:02d}",
                    owner=task.owner,
                    policy_note=policy_note,
                )
            )
    return events

