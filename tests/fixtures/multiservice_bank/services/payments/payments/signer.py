"""SYNTHETIC fixture: payment instruction signer. Mentions RSA and SHA1 in a docstring (HN)."""

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding

from ledger.client import post_entry

JWS_SIGNING_ALG = "ES256"
KEY_WRAP_ALGORITHM = "RSA-OAEP"
TOKEN_HMAC_ALG = "HS256"  # HN: HMAC is not a migration target
ERROR_ALG_MESSAGE = "RS256 is not supported"  # HN: free text, not an identifier
rsa_report_title = "RSA usage"  # HN: lower-case look-alike


def sign(key, data: bytes) -> bytes:
    sig = key.sign(data, ec.ECDSA(hashes.SHA256()))
    post_entry(sig)
    return sig


def wrap(public_key, dek: bytes) -> bytes:
    return public_key.encrypt(dek, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))


def describe(alg: str) -> str:
    LOCAL_ALG = "RS256"  # HN: function-local, not a module constant
    return LOCAL_ALG + alg
