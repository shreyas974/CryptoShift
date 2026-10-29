"""Parameter-set conformance check.

Compares the byte sizes the crypto provider declares for post-quantum
parameter sets with the sizes published in FIPS 203 (ML-KEM) and FIPS 204
(ML-DSA). This catches pre-standard builds. It is NOT a known-answer test and
does not prove the implementation computes correct outputs.

Usage: python -m tools.conformance ALG [ALG ...]  (prints JSON to stdout)
"""

import json
import sys

from shared.bankcrypto import primitives

# (public key, secret key, ciphertext or signature) in bytes.
FIPS_SIZES = {
    "ML-KEM-512": (800, 1632, 768),
    "ML-KEM-768": (1184, 2400, 1088),
    "ML-KEM-1024": (1568, 3168, 1568),
    "ML-DSA-44": (1312, 2560, 2420),
    "ML-DSA-65": (1952, 4032, 3309),
    "ML-DSA-87": (2592, 4896, 4627),
}


def check(algorithm):
    expected = FIPS_SIZES.get(algorithm)
    declared = primitives.DECLARED_SIZES.get(algorithm)
    if expected is None:
        return {"algorithm": algorithm, "status": "not_applicable", "detail": "No FIPS 203/204 size table for this algorithm"}
    if declared is None:
        return {"algorithm": algorithm, "status": "failed", "detail": "Provider does not support this parameter set"}
    labels = ("public key", "secret key", "signature/ciphertext")
    diffs = [f"{label}: declared {d} B, FIPS {e} B" for label, d, e in zip(labels, declared, expected) if d != e]
    if diffs:
        return {"algorithm": algorithm, "status": "failed", "detail": "; ".join(diffs)}
    return {"algorithm": algorithm, "status": "passed", "detail": "Declared sizes match " + ("FIPS 203" if "KEM" in algorithm else "FIPS 204")}


def main():
    print(json.dumps([check(a) for a in sys.argv[1:]]))


if __name__ == "__main__":
    main()
