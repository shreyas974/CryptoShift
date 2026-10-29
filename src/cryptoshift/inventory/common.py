"""Shared helpers for the Stage 1 inventory detectors: candidate mapping, redaction, finding construction.

Mapping policy (candidates for human review, never automatic):
- key_establishment  -> ML-KEM (FIPS 203)
- digital_signature  -> ML-DSA (FIPS 204) or SLH-DSA (FIPS 205)
- unknown purpose    -> HOLD for human review (via rules.resolve_contextual_pqc_rule)
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Dict, Optional

from cryptoshift.models import CryptoFinding
from cryptoshift.optimization.auth_check import redact_secrets
from cryptoshift.rules import resolve_contextual_pqc_rule

ASYMMETRIC_FAMILIES = {"RSA", "EC", "ECDSA", "ECDH", "DH", "DSA", "X25519", "X448", "Ed25519", "Ed448"}
PQC_FAMILIES = {"ML-KEM", "ML-DSA", "SLH-DSA", "Hybrid-ML-KEM"}

SNIPPET_MAX = 160
_SECRET_ASSIGN_RE = re.compile(
    r"((?:password|passwd|secret|token|api[_-]?key|private[_-]?key|passphrase)\w*\s*[=:]\s*)(['\"]).*?\2",
    re.IGNORECASE,
)


_ALGORITHM_TOKEN_RE = re.compile(
    r"(?:TLS|SSL)_[A-Z0-9_]+"  # IANA cipher suite names (upper-case only)
    r"|[A-Za-z0-9]+/[A-Z0-9]{2,5}/[A-Za-z0-9-]*Padding"  # JCA transformations, e.g. RSA/ECB/OAEPWith...Padding
    r"|[A-Za-z0-9-]*With[A-Za-z0-9-]*And[A-Za-z0-9-]*"  # JCA names such as OAEPWithSHA-256AndMGF1Padding
)


def _mask_long_token(m: "re.Match[str]") -> str:
    return m.group(0) if _ALGORITHM_TOKEN_RE.fullmatch(m.group(0)) else "[REDACTED_TOKEN]"


def redact_snippet(line: str) -> str:
    """Return a short, safe snippet: secrets, long key-like tokens and user paths are masked.

    Long tokens are masked unless they have the exact shape of an algorithm identifier (IANA suite or JCA name)."""
    text = line.strip()
    if "PRIVATE KEY" in text or "BEGIN CERTIFICATE" in text:
        return "[REDACTED: key/certificate material]"
    text = _SECRET_ASSIGN_RE.sub(r"\1\2[REDACTED]\2", text)
    text = re.sub(r"[A-Za-z0-9+/=_\-]{32,}", _mask_long_token, text)
    text = redact_secrets(text)
    if len(text) > SNIPPET_MAX:
        text = text[: SNIPPET_MAX - 3] + "..."
    return text


def is_test_path(rel_path: str) -> bool:
    parts = PurePosixPath(rel_path).parts
    name = parts[-1] if parts else ""
    return (
        any(p in ("test", "tests", "testing") for p in parts[:-1])
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


def candidate_mapping(family: str, purpose: str) -> Dict[str, str]:
    """Purpose-dependent candidate (for human review) with threat note and severity."""
    if family in PQC_FAMILIES:
        return {
            "quantum_threat": "None identified (PQC or hybrid PQC primitive present)",
            "target_pqc_algorithm": "No migration candidate (already PQC/hybrid); verify parameters and fallback",
            "nist_standard": "FIPS 203 / FIPS 204 / FIPS 205",
            "severity": "INFO",
        }
    if purpose == "unknown":
        rule = resolve_contextual_pqc_rule(family, "unknown")
        return {
            "quantum_threat": rule["quantum_threat"],
            "target_pqc_algorithm": rule["target_pqc"],
            "nist_standard": rule["nist_standard"],
            "severity": rule["severity"],
        }
    if purpose == "key_establishment" and family in ASYMMETRIC_FAMILIES:
        return {
            "quantum_threat": "Shor-CRQC (harvest-now-decrypt-later exposure of key establishment)",
            "target_pqc_algorithm": "Candidate: ML-KEM (FIPS 203), e.g. ML-KEM-768 or hybrid X25519MLKEM768 in TLS 1.3",
            "nist_standard": "FIPS 203 (ML-KEM)",
            "severity": "CRITICAL",
        }
    if purpose == "digital_signature" and family in ASYMMETRIC_FAMILIES:
        return {
            "quantum_threat": "Shor-CRQC (signature forgery once a CRQC exists)",
            "target_pqc_algorithm": "Candidate: ML-DSA (FIPS 204) or SLH-DSA (FIPS 205), subject to library/peer support",
            "nist_standard": "FIPS 204 (ML-DSA) / FIPS 205 (SLH-DSA)",
            "severity": "CRITICAL",
        }
    if purpose == "symmetric_encryption":
        return {
            "quantum_threat": "Classically weak cipher (small block/key); Grover further reduces margin",
            "target_pqc_algorithm": "Candidate: AES-256-GCM",
            "nist_standard": "NIST SP 800-38D",
            "severity": "HIGH",
        }
    if purpose == "message_digest":
        return {
            "quantum_threat": "Classically broken collision resistance",
            "target_pqc_algorithm": "Candidate: SHA-256/SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202)",
            "nist_standard": "FIPS 180-4 / FIPS 202",
            "severity": "HIGH",
        }
    if purpose == "transport_protocol":
        return {
            "quantum_threat": "Protocol version cannot negotiate hybrid ML-KEM groups (TLS 1.3 required)",
            "target_pqc_algorithm": "Candidate: TLS 1.3 only, then hybrid ML-KEM groups (e.g. X25519MLKEM768)",
            "nist_standard": "RFC 8446 / NIST SP 800-52r2",
            "severity": "HIGH",
        }
    return {
        "quantum_threat": "Review required",
        "target_pqc_algorithm": "HOLD: requires human review",
        "nist_standard": "n/a",
        "severity": "MEDIUM",
    }


def make_finding(
    *,
    index: int,
    rel_path: str,
    line: int,
    family: str,
    purpose: str,
    detector: str,
    detected_value: str,
    reason: str,
    confidence: str,
    ambiguity: str = "none",
    evidence_type: str = "source_code",
    library_or_protocol: str = "unknown",
    snippet: str = "",
    location: Optional[str] = None,
    service_id: str = "scanned_repo",
    algorithm_label: Optional[str] = None,
    service_id_basis: str = "",
    service_id_confidence: str = "",
) -> CryptoFinding:
    if ambiguity == "unknown" and purpose != "unknown":
        purpose = "unknown"
    cand = candidate_mapping(family, purpose)
    return CryptoFinding(
        finding_id=f"INV-{index:04d}",
        service_id=service_id,
        file_path=rel_path,
        line_number=line,
        legacy_algorithm=algorithm_label or family,
        quantum_threat=cand["quantum_threat"],
        target_pqc_algorithm=cand["target_pqc_algorithm"],
        nist_standard=cand["nist_standard"],
        severity=cand["severity"],
        evidence_type=evidence_type,
        operation_purpose=purpose,
        confidence=confidence,
        rationale=reason,
        owner="unknown",
        library_or_protocol=library_or_protocol,
        human_review_status="requires_human_review",
        detector=detector,
        algorithm_family=family,
        detected_value=redact_snippet(detected_value)[:200],
        location=location or f"line {line}",
        snippet_redacted=redact_snippet(snippet) if snippet else "",
        ambiguity=ambiguity,
        in_test_file=is_test_path(rel_path),
        service_id_basis=service_id_basis,
        service_id_confidence=service_id_confidence,
    )
