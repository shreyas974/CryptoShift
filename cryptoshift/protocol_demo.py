"""Synthetic protocol handshake demo comparing legacy RSA/ECDSA with Hybrid FIPS 203/204 envelopes."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, Dict


def run_hybrid_protocol_demo() -> Dict[str, Any]:
    """Run a deterministic synthetic comparison of classical vs. hybrid PQC message protection."""
    payload = b"ISO20022:PACS.008:TXN=900142:AMOUNT=250000.00:CURRENCY=INR"
    classical_digest = hashlib.sha1(payload).hexdigest()
    pqc_digest = hashlib.sha3_256(payload).hexdigest()
    hybrid_mac = hmac.new(b"SYNTHETIC_MLKEM768_SHARED_SECRET_SEED", payload, hashlib.sha3_256).hexdigest()
    return {
        "payload_type": "ISO-20022 pacs.008 Interbank Credit Transfer (Synthetic)",
        "legacy_envelope": {
            "key_exchange": "ECDHE-P256",
            "signature": "RSA-2048",
            "digest_alg": "SHA-1",
            "digest_hex": classical_digest,
            "quantum_safe": False,
        },
        "hybrid_pqc_envelope": {
            "key_exchange": "X25519 + ML-KEM-768 (FIPS 203 Hybrid)",
            "signature": "ECDSA-P256 + ML-DSA-65 (FIPS 204 Dual-Sign)",
            "digest_alg": "SHA3-256",
            "digest_hex": pqc_digest,
            "hybrid_authenticator_tag": hybrid_mac[:32],
            "quantum_safe": True,
        },
    }
