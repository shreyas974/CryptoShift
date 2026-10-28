"""Explainable, configurable risk scoring for banking cryptographic migration tasks."""

from __future__ import annotations

from typing import Dict, List

from cryptoshift.models import MigrationTask
from cryptoshift.rules import resolve_contextual_pqc_rule
from cryptoshift.scanner import SERVICE_PURPOSE_CONTEXT
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
    """Compute a transparent, reproducible quantum-exposure urgency score in [1.0, 10.0]."""
    alg_score = sum(ALGORITHM_BASE_RISK.get(a, 3.0) for a in legacy_algorithms) / max(len(legacy_algorithms), 1)
    mult = CRITICALITY_MULTIPLIER.get(criticality, 1.0)
    retention_bonus = min(retention_years / 10.0, 1.5)
    return round(min(10.0, alg_score * mult + retention_bonus), 2)


def build_migration_tasks() -> List[MigrationTask]:
    """Build the canonical list of 6 banking service migration tasks with context-aware PQC targets."""
    tasks: List[MigrationTask] = []
    for service_id, meta in SYNTHETIC_BANK_SERVICES.items():
        legacy = list(meta["legacy_algorithms"])
        targets: List[str] = []
        owner = "Banking Platform Engineering"
        for alg in legacy:
            ctx = SERVICE_PURPOSE_CONTEXT.get((service_id, alg), {"purpose": "unknown", "owner": owner})
            owner = ctx.get("owner", owner)
            rule = resolve_contextual_pqc_rule(alg, ctx["purpose"])
            targets.append(f"{rule['target_pqc']} [{ctx['purpose']}]")

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
                owner=owner,
            )
        )
    return tasks

