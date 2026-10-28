"""Synthetic fixture SYN-010: Already migrated PQC service (True Negative)."""

import hashlib

KEM_ALGORITHM = "X25519MLKEM768"
SIGNATURE_ALGORITHM = "ML-DSA-65"


def modern_digest(payload: bytes) -> str:
    return hashlib.sha3_256(payload).hexdigest()

