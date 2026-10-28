"""Context-aware NIST Post-Quantum Cryptography (FIPS 203 / 204 / 205) mapping rules.

Important Cryptographic Role Distinction:
- **ML-KEM (NIST FIPS 203)** is exclusively for **key establishment / key encapsulation**.
- **ML-DSA (NIST FIPS 204)** and **SLH-DSA (NIST FIPS 205)** are exclusively for **digital signatures**.
- **AES-256-GCM** is for **symmetric authenticated encryption**.
- **SHA3-256 / SHA-384** is for **cryptographic hashing / message digests**.

An algorithm clue (such as `RSA-2048`) must never be mapped to a PQC replacement without first
identifying the **operation purpose** (`key_establishment` vs. `digital_signature` vs. `unknown`).
"""

from __future__ import annotations

from typing import Dict, Tuple

# Context-aware mapping keyed by (legacy_algorithm, operation_purpose)
CONTEXTUAL_PQC_RULES: Dict[Tuple[str, str], Dict[str, str]] = {
    ("RSA-2048", "digital_signature"): {
        "quantum_threat": "Shor-CRQC (Integer factorization broken by cryptanalytically relevant quantum computer)",
        "target_pqc": "ML-DSA-65 + RSA-2048 Hybrid Signature",
        "nist_standard": "FIPS 204 (ML-DSA)",
        "severity": "CRITICAL",
    },
    ("RSA-2048", "key_establishment"): {
        "quantum_threat": "Shor-CRQC (Harvest-Now-Decrypt-Later key transport/wrapping exposure)",
        "target_pqc": "ML-KEM-768 (FIPS 203) Hybrid Key Encapsulation",
        "nist_standard": "FIPS 203 (ML-KEM)",
        "severity": "CRITICAL",
    },
    ("ECDSA-P256", "digital_signature"): {
        "quantum_threat": "Shor-CRQC (Elliptic curve discrete logarithm broken)",
        "target_pqc": "ML-DSA-65 + ECDSA-P256 Dual-Signature",
        "nist_standard": "FIPS 204 (ML-DSA)",
        "severity": "CRITICAL",
    },
    ("ECDHE-P256", "key_establishment"): {
        "quantum_threat": "Shor-CRQC (Harvest-Now-Decrypt-Later ephemeral key exchange risk)",
        "target_pqc": "X25519MLKEM768 Hybrid Key Establishment",
        "nist_standard": "FIPS 203 (ML-KEM)",
        "severity": "CRITICAL",
    },
    ("DH-2048", "key_establishment"): {
        "quantum_threat": "Shor-CRQC (Finite-field Diffie-Hellman key exchange broken)",
        "target_pqc": "ML-KEM-768 Hybrid Key Establishment",
        "nist_standard": "FIPS 203 (ML-KEM)",
        "severity": "CRITICAL",
    },
    ("3DES", "symmetric_encryption"): {
        "quantum_threat": "Grover-Weakened + Sweet32 64-bit block collision vulnerability",
        "target_pqc": "AES-256-GCM",
        "nist_standard": "NIST SP 800-38D",
        "severity": "HIGH",
    },
    ("SHA-1", "message_digest"): {
        "quantum_threat": "Classical collision broken + Grover preimage reduction",
        "target_pqc": "SHA3-256 / SHA-384",
        "nist_standard": "FIPS 202 (SHA-3)",
        "severity": "HIGH",
    },
}

# Default fallback summary table for legacy algorithm lookup when purpose is inferred from service context
PQC_MIGRATION_RULES: Dict[str, Dict[str, str]] = {
    "RSA-2048": {
        "default_purpose": "digital_signature",
        "quantum_threat": "Shor-CRQC (Factorization broken in polynomial time)",
        "target_pqc": "Context-dependent: ML-DSA-65 (FIPS 204) for signatures; ML-KEM-768 (FIPS 203) for key encapsulation",
        "nist_standard": "FIPS 204 (ML-DSA) / FIPS 203 (ML-KEM)",
        "severity": "CRITICAL",
    },
    "ECDSA-P256": {
        "default_purpose": "digital_signature",
        "quantum_threat": "Shor-CRQC (Elliptic curve discrete log broken)",
        "target_pqc": "ML-DSA-65 + ECDSA-P256 Dual-Signature",
        "nist_standard": "FIPS 204 (ML-DSA)",
        "severity": "CRITICAL",
    },
    "ECDHE-P256": {
        "default_purpose": "key_establishment",
        "quantum_threat": "Shor-CRQC (Harvest-Now-Decrypt-Later key exchange risk)",
        "target_pqc": "X25519MLKEM768 Hybrid Key Establishment",
        "nist_standard": "FIPS 203 (ML-KEM)",
        "severity": "CRITICAL",
    },
    "DH-2048": {
        "default_purpose": "key_establishment",
        "quantum_threat": "Shor-CRQC (Finite-field discrete log broken)",
        "target_pqc": "ML-KEM-768 Hybrid Key Establishment",
        "nist_standard": "FIPS 203 (ML-KEM)",
        "severity": "CRITICAL",
    },
    "3DES": {
        "default_purpose": "symmetric_encryption",
        "quantum_threat": "Grover-Weakened + Sweet32 block collision (<64-bit effective security)",
        "target_pqc": "AES-256-GCM",
        "nist_standard": "NIST SP 800-38D",
        "severity": "HIGH",
    },
    "SHA-1": {
        "default_purpose": "message_digest",
        "quantum_threat": "Collision broken classically + Grover preimage reduction",
        "target_pqc": "SHA3-256 / SHA-384",
        "nist_standard": "FIPS 202 (SHA-3)",
        "severity": "HIGH",
    },
}


def resolve_contextual_pqc_rule(legacy_algorithm: str, operation_purpose: str) -> Dict[str, str]:
    """Return a context-aware PQC recommendation based on both algorithm clue and operation purpose."""
    if operation_purpose == "unknown":
        return {
            "quantum_threat": "Potential quantum-vulnerable primitive (operation purpose unresolved)",
            "target_pqc": "HOLD: Requires human review of operation purpose (ML-KEM for key establishment vs. ML-DSA for signatures)",
            "nist_standard": "Pending Purpose Classification (FIPS 203 vs. FIPS 204)",
            "severity": "MEDIUM",
        }
    exact = CONTEXTUAL_PQC_RULES.get((legacy_algorithm, operation_purpose))
    if exact:
        return exact
    return PQC_MIGRATION_RULES.get(
        legacy_algorithm,
        {
            "quantum_threat": "Quantum-vulnerable primitive",
            "target_pqc": "Requires human review (FIPS 203 ML-KEM or FIPS 204 ML-DSA)",
            "nist_standard": "FIPS 203 / FIPS 204",
            "severity": "HIGH",
        },
    )

