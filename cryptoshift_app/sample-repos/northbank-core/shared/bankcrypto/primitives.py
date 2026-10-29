"""NorthBank crypto provider facade.

This is a deterministic stand-in for the bank's real crypto provider so the
repository can be scanned and tested without native libraries. It performs no
real cryptography: it records which algorithm and parameter set a caller asked
for, and returns objects with the byte sizes the provider *declares*.
"""

import hashlib
from dataclasses import dataclass

# Byte sizes this provider build declares for each parameter set.
# (public key, secret key, signature or ciphertext)
DECLARED_SIZES = {
    "RSA-1024": (162, 634, 128),
    "RSA-2048": (294, 1218, 256),
    "RSA-3072": (422, 1793, 384),
    "ECDSA-P256": (65, 32, 72),
    "ECDH-P256": (65, 32, 0),
    "X25519": (32, 32, 0),
    "ML-KEM-768": (1184, 2400, 1088),
    "ML-KEM-1024": (1568, 3168, 1568),
    "ML-DSA-44": (1312, 2560, 2420),
    "ML-DSA-65": (1952, 4032, 3309),
    # Pre-standard (round-3 Dilithium5) sizes left over from an earlier build.
    "ML-DSA-87": (2592, 4864, 4595),
}

SUPPORTED_HASHES = ("SHA1", "SHA-256", "SHA-384")


@dataclass(frozen=True)
class KeyPair:
    algorithm: str
    public_key_bytes: int
    secret_key_bytes: int


@dataclass(frozen=True)
class Signature:
    algorithm: str
    length: int
    digest: str


def generate_keypair(algorithm, bits=None):
    name = f"{algorithm}-{bits}" if bits else algorithm
    if name not in DECLARED_SIZES:
        raise ValueError(f"unsupported algorithm {name}")
    pk, sk, _ = DECLARED_SIZES[name]
    return KeyPair(name, pk, sk)


def sign(keypair, message: bytes):
    _, _, sig = DECLARED_SIZES[keypair.algorithm]
    digest = hashlib.sha256(keypair.algorithm.encode() + message).hexdigest()
    return Signature(keypair.algorithm, sig, digest)


def verify(keypair, message: bytes, signature):
    return signature.algorithm == keypair.algorithm and signature == sign(keypair, message)


def checksum(algorithm, data: bytes):
    if algorithm not in SUPPORTED_HASHES:
        raise ValueError(f"unsupported hash {algorithm}")
    name = {"SHA1": "sha1", "SHA-256": "sha256", "SHA-384": "sha384"}[algorithm]
    return hashlib.new(name, data).hexdigest()


def seal(algorithm, key_id, plaintext: bytes):
    if algorithm != "AES-256-GCM":
        raise ValueError(f"unsupported cipher {algorithm}")
    return {"alg": algorithm, "kid": key_id, "len": len(plaintext) + 16}
