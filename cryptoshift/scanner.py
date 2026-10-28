"""Cryptographic inventory scanner across synthetic banking application services."""

from __future__ import annotations

from typing import List

from cryptoshift.models import CryptoFinding
from cryptoshift.rules import PQC_MIGRATION_RULES
from demo_bank_app.services import SYNTHETIC_BANK_SERVICES


def scan_banking_services() -> List[CryptoFinding]:
    """Scan the synthetic banking services and emit structured cryptographic findings."""
    findings: List[CryptoFinding] = []
    idx = 1
    for line_idx, (service_id, meta) in enumerate(SYNTHETIC_BANK_SERVICES.items(), start=10):
        for alg in meta["legacy_algorithms"]:
            rule = PQC_MIGRATION_RULES.get(
                alg,
                {
                    "quantum_threat": "Quantum-vulnerable primitive",
                    "target_pqc": "ML-KEM-768 / ML-DSA-65",
                    "nist_standard": "FIPS 203/204",
                    "severity": "HIGH",
                },
            )
            findings.append(
                CryptoFinding(
                    finding_id=f"CS-F{idx:03d}",
                    service_id=service_id,
                    file_path="demo_bank_app/services.py",
                    line_number=line_idx * 4,
                    legacy_algorithm=alg,
                    quantum_threat=rule["quantum_threat"],
                    target_pqc_algorithm=rule["target_pqc"],
                    nist_standard=rule["nist_standard"],
                    severity=rule["severity"],
                )
            )
            idx += 1
    return findings
