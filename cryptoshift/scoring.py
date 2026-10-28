"""Mosca urgency and Harvest-Now-Decrypt-Later (HNDL) risk scoring for banking services."""

from __future__ import annotations

from typing import Dict, List

from cryptoshift.models import MigrationTask
from cryptoshift.rules import PQC_MIGRATION_RULES
from demo_bank_app.services import SYNTHETIC_BANK_SERVICES

ALGORITHM_BASE_RISK: Dict[str, float] = {
    "ECDHE-P256": 4.8,
    "RSA-2048": 4.5,
    "ECDSA-P256": 4.3,
    "DH-2048": 4.4,
    "3DES": 3.2,
    "SHA-1": 3.0,
}

CRITICALITY_MULTIPLIER: Dict[str, float] = {
    "CRITICAL": 1.25,
    "HIGH": 1.0,
    "MEDIUM": 0.8,
}


def compute_service_risk(legacy_algorithms: List[str], criticality: str, retention_years: int) -> float:
    """Compute a transparent, reproducible quantum-exposure risk score in [1.0, 10.0]."""
    alg_score = sum(ALGORITHM_BASE_RISK.get(a, 3.0) for a in legacy_algorithms) / max(len(legacy_algorithms), 1)
    mult = CRITICALITY_MULTIPLIER.get(criticality, 1.0)
    retention_bonus = min(retention_years / 10.0, 1.5)
    return round(min(10.0, alg_score * mult + retention_bonus), 2)


def build_migration_tasks() -> List[MigrationTask]:
    """Build the canonical list of 6 banking service migration tasks for wave scheduling."""
    tasks: List[MigrationTask] = []
    for service_id, meta in SYNTHETIC_BANK_SERVICES.items():
        legacy = list(meta["legacy_algorithms"])
        targets = [PQC_MIGRATION_RULES[a]["target_pqc"] for a in legacy if a in PQC_MIGRATION_RULES]
        risk = compute_service_risk(
            legacy_algorithms=legacy,
            criticality=meta["criticality"],
            retention_years=int(meta["data_retention_years"]),
        )
        tasks.append(
            MigrationTask(
                service_id=service_id,
                name=meta["name"],
                legacy_algorithms=legacy,
                target_algorithms=targets,
                dependencies=list(meta["dependencies"]),
                duration_minutes=int(meta["duration_minutes"]),
                rollout_cost=float(meta["rollout_cost"]),
                risk_score=risk,
                verification_ready_wave0=bool(meta["verification_ready_wave0"]),
                criticality=meta["criticality"],
            )
        )
    return tasks
