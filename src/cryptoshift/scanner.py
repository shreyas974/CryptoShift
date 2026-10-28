"""Context-aware cryptographic inventory scanner across source, configuration, and synthetic banking services."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

from cryptoshift.models import CryptoFinding
from cryptoshift.rules import resolve_contextual_pqc_rule
from demo_bank_app.services import SYNTHETIC_BANK_SERVICES

# Service-level context map for the synthetic banking fixture
SERVICE_PURPOSE_CONTEXT: Dict[Tuple[str, str], Dict[str, str]] = {
    ("auth_gateway", "RSA-2048"): {
        "purpose": "digital_signature",
        "protocol": "OAuth2 / OIDC JWT RS256 Token Signing",
        "owner": "Identity & Access Team",
        "confidence": "high",
        "rationale": "Service issues signed JWT bearer tokens using RS256.",
    },
    ("auth_gateway", "SHA-1"): {
        "purpose": "message_digest",
        "protocol": "Legacy Token Thumbprint Digest",
        "owner": "Identity & Access Team",
        "confidence": "high",
        "rationale": "Certificate thumbprint calculation uses SHA-1.",
    },
    ("ledger_audit", "ECDSA-P256"): {
        "purpose": "digital_signature",
        "protocol": "Core Ledger Merkle-Root Notarization",
        "owner": "Core Ledger Team",
        "confidence": "high",
        "rationale": "Signs immutable audit batches with ECDSA secp256r1.",
    },
    ("ledger_audit", "SHA-1"): {
        "purpose": "message_digest",
        "protocol": "Legacy Audit Record Digest",
        "owner": "Core Ledger Team",
        "confidence": "high",
        "rationale": "Secondary legacy digest computed with SHA-1.",
    },
    ("interbank_tls", "ECDHE-P256"): {
        "purpose": "key_establishment",
        "protocol": "Interbank ISO-20022 mTLS Ephemeral Key Exchange",
        "owner": "Network & Interbank Connectivity Team",
        "confidence": "high",
        "rationale": "TLS session key establishment uses ECDHE over P-256.",
    },
    ("interbank_tls", "RSA-2048"): {
        "purpose": "digital_signature",
        "protocol": "Interbank mTLS Peer Certificate Authentication",
        "owner": "Network & Interbank Connectivity Team",
        "confidence": "high",
        "rationale": "mTLS leaf and intermediate certificates use RSA-2048 signatures.",
    },
    ("card_vault", "RSA-2048"): {
        "purpose": "key_establishment",
        "protocol": "PKCS#11 Vault DEK Key Wrapping (RSA-OAEP)",
        "owner": "Card Security & PCI Vault Team",
        "confidence": "high",
        "rationale": "RSA-2048 wraps symmetric data encryption keys (key establishment/encapsulation role).",
    },
    ("card_vault", "3DES"): {
        "purpose": "symmetric_encryption",
        "protocol": "Legacy Card PIN Block / Track Envelope Encryption",
        "owner": "Card Security & PCI Vault Team",
        "confidence": "high",
        "rationale": "Legacy payment HSM slot configured for Triple-DES.",
    },
    ("payment_signing", "ECDSA-P256"): {
        "purpose": "digital_signature",
        "protocol": "RTGS / UPI Payment Instruction Signature",
        "owner": "Real-Time Payments Team",
        "confidence": "high",
        "rationale": "Signs outbound payment instructions with ECDSA-P256.",
    },
    ("payment_signing", "RSA-2048"): {
        "purpose": "digital_signature",
        "protocol": "ISO-20022 XMLDSig Detached Signature",
        "owner": "Real-Time Payments Team",
        "confidence": "high",
        "rationale": "Fallback XMLDSig envelope signing uses RSA-2048.",
    },
    ("settlement_batch", "DH-2048"): {
        "purpose": "key_establishment",
        "protocol": "Clearinghouse SFTP/SSH Group14 Key Exchange",
        "owner": "Settlement & Treasury Operations",
        "confidence": "high",
        "rationale": "Batch transfer channel negotiates finite-field DH-2048 key exchange.",
    },
    ("settlement_batch", "RSA-2048"): {
        "purpose": "digital_signature",
        "protocol": "End-of-Day Settlement Manifest Signature",
        "owner": "Settlement & Treasury Operations",
        "confidence": "high",
        "rationale": "Batch settlement manifest is signed with RSA-2048.",
    },
    ("settlement_batch", "3DES"): {
        "purpose": "symmetric_encryption",
        "protocol": "Legacy Clearinghouse Batch Archive Cipher",
        "owner": "Settlement & Treasury Operations",
        "confidence": "high",
        "rationale": "Archive payload encrypted with 3DES-CBC for legacy partner.",
    },
}

# Patterns for source/config file scanning (used in dataset evaluation and file scanner)
LINE_DETECTION_PATTERNS: List[Tuple[re.Pattern[str], str, str, str]] = [
    (
        re.compile(r"\b(rsa\.generate_private_key|RS256|PKCS1v15|RSA_SIGN)\b", re.IGNORECASE),
        "RSA-2048",
        "digital_signature",
        "high",
    ),
    (
        re.compile(r"\b(RSA_OAEP|padding\.OAEP|RSA_KEY_WRAP|RSA_KEM)\b", re.IGNORECASE),
        "RSA-2048",
        "key_establishment",
        "high",
    ),
    (
        re.compile(r"\b(ec\.SECP256R1|ECDSA_P256|ES256|ec\.ECDSA)\b", re.IGNORECASE),
        "ECDSA-P256",
        "digital_signature",
        "high",
    ),
    (
        re.compile(r"\b(ECDHE[_-]RSA|ECDHE[_-]ECDSA|ECDHE[_-]P256|TLS_ECDHE)\b", re.IGNORECASE),
        "ECDHE-P256",
        "key_establishment",
        "high",
    ),
    (
        re.compile(r"\b(diffie-hellman-group14|DH_2048|dh\.generate_parameters)\b", re.IGNORECASE),
        "DH-2048",
        "key_establishment",
        "high",
    ),
    (
        re.compile(r"\b(TripleDES|3DES|DES3\.new)\b", re.IGNORECASE),
        "3DES",
        "symmetric_encryption",
        "high",
    ),
    (
        re.compile(r"\b(hashlib\.sha1|hashes\.SHA1)\b", re.IGNORECASE),
        "SHA-1",
        "message_digest",
        "high",
    ),
    # Generic RSA clue without clear operation context -> flagged with medium/low confidence
    (
        re.compile(r"\b(LEGACY_RSA_2048_CONFIG)\b"),
        "RSA-2048",
        "unknown",
        "medium",
    ),
]


def scan_banking_services() -> List[CryptoFinding]:
    """Scan the synthetic banking services and emit context-aware CBOM findings."""
    findings: List[CryptoFinding] = []
    idx = 1
    for line_idx, (service_id, meta) in enumerate(SYNTHETIC_BANK_SERVICES.items(), start=10):
        for alg in meta["legacy_algorithms"]:
            ctx = SERVICE_PURPOSE_CONTEXT.get(
                (service_id, alg),
                {
                    "purpose": "unknown",
                    "protocol": "Unspecified Banking Protocol",
                    "owner": "unknown",
                    "confidence": "medium",
                    "rationale": "Algorithm listed in service descriptor without explicit operation role.",
                },
            )
            rule = resolve_contextual_pqc_rule(alg, ctx["purpose"])
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
                    evidence_type="service_descriptor",
                    operation_purpose=ctx["purpose"],
                    confidence=ctx["confidence"],
                    rationale=ctx["rationale"],
                    owner=ctx["owner"],
                    library_or_protocol=ctx["protocol"],
                    human_review_status="requires_human_review",
                )
            )
            idx += 1
    return findings


def scan_source_file(file_path: Path, service_id: str = "scanned_repo") -> List[CryptoFinding]:
    """Scan a single source or config file for cryptographic clues with line-level evidence."""
    findings: List[CryptoFinding] = []
    if not file_path.is_file():
        return findings
    ext = file_path.suffix.lower()
    ev_type = "config_file" if ext in (".yaml", ".yml", ".json", ".ini", ".conf", ".toml") else "source_code"

    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return findings

    idx = 1
    for line_no, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for regex, alg_clue, purpose, confidence in LINE_DETECTION_PATTERNS:
            if regex.search(raw_line):
                rule = resolve_contextual_pqc_rule(alg_clue, purpose)
                findings.append(
                    CryptoFinding(
                        finding_id=f"SCAN-{file_path.stem}-{idx:02d}",
                        service_id=service_id,
                        file_path=str(file_path.as_posix()),
                        line_number=line_no,
                        legacy_algorithm=alg_clue,
                        quantum_threat=rule["quantum_threat"],
                        target_pqc_algorithm=rule["target_pqc"],
                        nist_standard=rule["nist_standard"],
                        severity=rule["severity"],
                        evidence_type=ev_type,
                        operation_purpose=purpose,
                        confidence=confidence,
                        rationale=f"Matched pattern '{regex.pattern}' on line {line_no}.",
                        owner="unknown",
                        library_or_protocol="static_file_scan",
                        human_review_status="requires_human_review",
                    )
                )
                idx += 1
                break
    return findings

