"""NIST Post-Quantum Cryptography (FIPS 203 / 204 / 205) migration rules for banking primitives."""

from __future__ import annotations

from typing import Dict

PQC_MIGRATION_RULES: Dict[str, Dict[str, str]] = {
    "RSA-2048": {
        "quantum_threat": "Shor-CRQC (Factorization broken in polynomial time)",
        "target_pqc": "ML-DSA-65 + RSA-2048 Hybrid / ML-KEM-768",
        "nist_standard": "FIPS 204 (ML-DSA) / FIPS 203 (ML-KEM)",
        "severity": "CRITICAL",
    },
    "ECDSA-P256": {
        "quantum_threat": "Shor-CRQC (Elliptic curve discrete log broken)",
        "target_pqc": "ML-DSA-65 Dual-Signature",
        "nist_standard": "FIPS 204 (ML-DSA)",
        "severity": "CRITICAL",
    },
    "ECDHE-P256": {
        "quantum_threat": "Shor-CRQC (Harvest-Now-Decrypt-Later key exchange risk)",
        "target_pqc": "X25519MLKEM768 Hybrid Key Exchange",
        "nist_standard": "FIPS 203 (ML-KEM)",
        "severity": "CRITICAL",
    },
    "DH-2048": {
        "quantum_threat": "Shor-CRQC (Finite-field discrete log broken)",
        "target_pqc": "ML-KEM-768 + SLH-DSA-128s",
        "nist_standard": "FIPS 203 / FIPS 205",
        "severity": "CRITICAL",
    },
    "3DES": {
        "quantum_threat": "Grover-Weakened + Sweet32 block collision (<64-bit effective security)",
        "target_pqc": "AES-256-GCM",
        "nist_standard": "NIST SP 800-38D (128-bit post-Grover security)",
        "severity": "HIGH",
    },
    "SHA-1": {
        "quantum_threat": "Collision broken classically + Grover preimage reduction",
        "target_pqc": "SHA3-256 / SHA-384",
        "nist_standard": "FIPS 202 (SHA-3)",
        "severity": "HIGH",
    },
}
