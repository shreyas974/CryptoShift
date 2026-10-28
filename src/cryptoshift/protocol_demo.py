"""Mocked/modelled protocol envelope trace and wire-overhead methodology for CryptoShift (PQC-01).

Important Disclosure:
- Hash digests (`SHA-1`, `SHA3-256`) and `HMAC-SHA3-256` tags are computed using Python's standard `hashlib`/`hmac`.
- The `X25519MLKEM768` (FIPS 203) and `ML-DSA-65` (FIPS 204) wire sizes and handshake fields are **MOCKED / MODELLED
  traces** based on official NIST FIPS 203 and FIPS 204 parameter specifications, NOT a live network TLS capture.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, Dict


def run_hybrid_protocol_demo() -> Dict[str, Any]:
    """Run a deterministic, explicitly labelled comparison of classical vs. hybrid PQC envelope overhead."""
    payload = b"ISO20022:PACS.008:TXN=900142:AMOUNT=250000.00:CURRENCY=INR"
    classical_digest = hashlib.sha1(payload).hexdigest()
    pqc_digest = hashlib.sha3_256(payload).hexdigest()
    hybrid_mac = hmac.new(b"SYNTHETIC_MLKEM768_SHARED_SECRET_SEED", payload, hashlib.sha3_256).hexdigest()

    return {
        "trace_classification": "MOCKED_PROTOCOL_TRACE (Real hashlib digests + NIST FIPS 203/204 specification byte sizes)",
        "payload_type": "ISO-20022 pacs.008 Interbank Credit Transfer (Synthetic Fixture)",
        "legacy_envelope": {
            "key_establishment": "ECDHE-P256 (32-byte public share)",
            "digital_signature": "RSA-2048 (256-byte signature, 256-byte public key)",
            "digest_alg": "SHA-1",
            "digest_hex": classical_digest,
            "estimated_handshake_bytes": 544,
            "quantum_safe": False,
        },
        "hybrid_pqc_envelope": {
            "key_establishment": "X25519 + ML-KEM-768 (FIPS 203 Hybrid: 32B + 1184B public key, 32B + 1088B ciphertext)",
            "digital_signature": "ECDSA-P256 + ML-DSA-65 (FIPS 204 Dual-Sign: ~64B + 3309B signature, 1952B ML-DSA pubkey)",
            "digest_alg": "SHA3-256",
            "digest_hex": pqc_digest,
            "hybrid_authenticator_tag": hybrid_mac[:32],
            "estimated_handshake_bytes": 7661,
            "quantum_safe_target": "Hybrid transitional protection (subject to implementation & side-channel validation)",
        },
        "overhead_methodology": {
            "wire_size_delta_bytes": 7661 - 544,
            "mtu_fragmentation_note": (
                "Hybrid key share + dual signature increases handshake payload by ~7.1 KB, exceeding a single "
                "1500-byte Ethernet MTU and requiring TCP segmentation / TLS record fragmentation checks."
            ),
            "measurement_method": "Analytical byte-budget calculation from NIST FIPS 203 (Table 2) & FIPS 204 (Table 1) parameters.",
        },
    }

