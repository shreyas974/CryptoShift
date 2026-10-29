"""Closed vocabulary of algorithm identifiers shared by the constant, structured-config, shell and Java detectors.

`classify_identifier(value)` only recognises exact identifiers (JWS/JWE names, Java JCA names, SSH names, key-type
names, protocol names). Free text such as "RS256 not supported" is not an identifier and returns nothing, which is
what keeps the scoped "algorithm constant" rule from firing on log or error strings.

Detection tuple: (family, purpose, ambiguity, confidence, reason).
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

Detection = Tuple[str, str, str, str, str]

VERSION = "algorithm_ids/1.0"

_WEAK_HASH = {"SHA1": "SHA-1", "SHA-1": "SHA-1", "SHA": "SHA-1", "MD5": "MD5", "MD4": "MD4", "MD2": "MD2"}
_PQC_RE = re.compile(r"^(ML-?KEM|ML-?DSA|SLH-?DSA|MLKEM|MLDSA|X25519MLKEM|SECP256R1MLKEM|SECP384R1MLKEM|KYBER|DILITHIUM)", re.I)
_TLS_OLD = {"SSLV2": "SSLv2", "SSLV3": "SSLv3", "TLSV1": "TLSv1", "TLSV1.0": "TLSv1", "TLS1.0": "TLSv1", "TLS1": "TLSv1",
            "TLSV1_0": "TLSv1", "TLS1_0": "TLSv1", "TLSV1.1": "TLSv1.1", "TLS1.1": "TLSv1.1", "TLSV1_1": "TLSv1.1",
            "TLS1_1": "TLSv1.1"}
_CURVES = {"P-256", "P256", "P-384", "P384", "P-521", "P521", "SECP256R1", "SECP384R1", "SECP521R1", "PRIME256V1",
           "SECP256K1", "NISTP256", "NISTP384", "NISTP521", "BRAINPOOLP256R1", "BRAINPOOLP384R1", "BRAINPOOLP512R1"}


def _norm(value: str) -> str:
    v = value.strip().strip("'\"").strip()
    return v.upper()


def is_pqc(value: str) -> bool:
    return bool(_PQC_RE.match(value.strip().strip("'\"")))


def classify_identifier(value: str, context: str = "") -> List[Detection]:
    """Classify one exact identifier. `context` (a key or variable name) only refines the purpose of curves."""
    raw = value.strip().strip("'\"").strip()
    v = raw.upper()
    ctx = context.lower()
    if not v or len(v) > 80 or " " in v:
        return []
    if is_pqc(raw):
        return [("Hybrid-ML-KEM" if "KEM" in v or "KYBER" in v else "ML-DSA", "key_establishment" if "KEM" in v or "KYBER" in v
                 else "digital_signature", "none", "high", f"PQC/hybrid identifier '{raw}'")]
    # JWS / JWE (RFC 7518)
    m = re.fullmatch(r"(RS|PS)(256|384|512)", v)
    if m:
        return [("RSA", "digital_signature", "none", "high", f"JWS algorithm {raw} (RSA signature)")]
    if re.fullmatch(r"ES(256|384|512|256K)", v):
        return [("ECDSA", "digital_signature", "none", "high", f"JWS algorithm {raw} (ECDSA signature)")]
    if v in ("EDDSA", "ED25519", "ED448"):
        return [("Ed25519" if v != "ED448" else "Ed448", "digital_signature", "none", "high", f"{raw} signature algorithm")]
    if v in ("RSA1_5", "RSA-OAEP", "RSA-OAEP-256", "RSA_OAEP", "RSA_OAEP_256", "RSAES-OAEP", "RSA-OAEP-384", "RSA-OAEP-512"):
        return [("RSA", "key_establishment", "none", "high", f"{raw}: RSA encryption / key transport")]
    if re.fullmatch(r"ECDH-ES(\+A(128|192|256)KW)?", v):
        return [("ECDH", "key_establishment", "none", "high", f"JWE algorithm {raw} (ECDH key agreement)")]
    if v in ("PKCS1V15", "PKCS1_V1_5", "PKCS1-V1_5", "PKCS1PADDING"):
        return [("RSA", "unknown", "ambiguous", "medium", f"{raw}: PKCS#1 v1.5 padding (signature or encryption)")]
    if v in ("PSS", "RSASSA-PSS", "RSA-PSS", "RSAPSS"):
        return [("RSA", "digital_signature", "none", "high", f"{raw}: RSA-PSS signature")]
    # Java JCA signature names: SHA256withRSA, SHA1withECDSA, SHA256withRSA/PSS, NONEwithRSA ...
    m = re.fullmatch(r"(NONE|MD2|MD5|SHA1?|SHA-?(?:1|224|256|384|512)|SHA3-(?:224|256|384|512))WITH(RSA|ECDSA|DSA|RSAANDMGF1|RSA/PSS|PLAIN-ECDSA)(?:INP1363FORMAT)?", v)
    if m:
        h, alg = m.group(1).replace("-", ""), m.group(2)
        fam = "ECDSA" if "ECDSA" in alg else "DSA" if alg == "DSA" else "RSA"
        out: List[Detection] = [(fam, "digital_signature", "none", "high", f"signature algorithm {raw}")]
        weak = {"SHA1": "SHA-1", "SHA": "SHA-1", "MD5": "MD5", "MD2": "MD2"}.get(h)
        if weak:
            out.append((weak, "message_digest", "none", "high", f"signature algorithm {raw} uses {weak}"))
        return out
    # SSH algorithm names (RFC 4253 / 5656 / 8332)
    if v in ("SSH-RSA", "RSA-SHA2-256", "RSA-SHA2-512"):
        return [("RSA", "digital_signature", "none", "high", f"SSH host/user key algorithm {raw}")]
    if v == "SSH-DSS":
        return [("DSA", "digital_signature", "none", "high", "SSH DSA key algorithm ssh-dss")]
    if v.startswith("ECDSA-SHA2-"):
        return [("ECDSA", "digital_signature", "none", "high", f"SSH ECDSA key algorithm {raw}")]
    if v in ("SSH-ED25519",):
        return [("Ed25519", "digital_signature", "none", "high", "SSH Ed25519 key algorithm")]
    if v.startswith("DIFFIE-HELLMAN-GROUP"):
        return [("DH", "key_establishment", "none", "high", f"SSH key exchange {raw} (finite-field DH)")]
    if v.startswith("ECDH-SHA2-") or v in ("CURVE25519-SHA256", "CURVE25519-SHA256@LIBSSH.ORG"):
        return [("ECDH", "key_establishment", "none", "high", f"SSH key exchange {raw} (ECDH)")]
    # Key-type names, optionally with a size: RSA, RSA-2048, RSA_2048, RSA:2048, rsa2048
    m = re.fullmatch(r"(RSA|DSA|EC|ECDSA|ECDH|ECDHE|DH|DHE|X25519|X448|DIFFIEHELLMAN|XDH)(?:[-_:]?(P-?\d{3}|\d{3,5}))?", v)
    if m:
        base, size = m.group(1), m.group(2)
        tail = f" ({size})" if size else ""
        if base == "RSA":
            return [("RSA", "unknown", "ambiguous", "medium", f"RSA key type{tail}; signing vs key transport not stated")]
        if base == "DSA":
            return [("DSA", "digital_signature", "none", "high", f"DSA key type{tail} (signature-only)")]
        if base == "ECDSA":
            return [("ECDSA", "digital_signature", "none", "high", f"ECDSA{tail}")]
        if base in ("ECDH", "ECDHE"):
            return [("ECDH", "key_establishment", "none", "high", f"{base}{tail} key agreement")]
        if base in ("DH", "DHE", "DIFFIEHELLMAN"):
            return [("DH", "key_establishment", "none", "high", f"finite-field {base}{tail}")]
        if base in ("X25519", "X448", "XDH"):
            return [("X25519" if base != "X448" else "X448", "key_establishment", "none", "high", f"{base} key agreement")]
        if base == "EC":
            return [("EC", "unknown", "ambiguous", "medium", f"EC key type{tail}; ECDSA vs ECDH not stated")]
    m = re.fullmatch(r"(ECDSA|ECDHE?)[-_](P-?\d{3}|SECP\d{3}R1|PRIME256V1)", v)
    if m:
        fam = "ECDSA" if m.group(1) == "ECDSA" else "ECDH"
        return [(fam, "digital_signature" if fam == "ECDSA" else "key_establishment", "none", "high", f"{raw}")]
    if v in _CURVES:
        if any(k in ctx for k in ("group", "curve", "kex", "exchange", "ecdh", "named")):
            return [("ECDH", "key_establishment", "none", "medium", f"classical curve/group {raw} in key-exchange setting")]
        return [("EC", "unknown", "ambiguous", "medium", f"elliptic curve {raw}; ECDSA vs ECDH not stated")]
    # Symmetric ciphers
    if v in ("3DES", "TRIPLEDES", "DESEDE", "DES-EDE3", "DES_EDE3", "DES-EDE3-CBC", "DES_EDE3_CBC", "DES-CBC3", "DESEDE/CBC/PKCS5PADDING", "TDEA"):
        return [("3DES", "symmetric_encryption", "none", "high", f"{raw}: Triple-DES")]
    if v in ("DES", "DES-CBC", "DES_CBC"):
        return [("DES", "symmetric_encryption", "none", "high", f"{raw}: single DES")]
    if v in ("RC4", "ARC4", "ARCFOUR"):
        return [("RC4", "symmetric_encryption", "none", "high", f"{raw}: RC4 stream cipher")]
    if v in ("BLOWFISH", "BF", "BF-CBC"):
        return [("Blowfish", "symmetric_encryption", "none", "high", f"{raw}: 64-bit block cipher")]
    # Hashes
    if v in _WEAK_HASH or v in ("HASHLIB.SHA1", "HASHLIB.MD5"):
        fam = _WEAK_HASH.get(v, "SHA-1" if "SHA1" in v else "MD5")
        return [(fam, "message_digest", "none", "high", f"{raw}: weak hash")]
    # Protocol versions
    if v in _TLS_OLD:
        return [("TLS-protocol", "transport_protocol", "none", "high", f"deprecated protocol {_TLS_OLD[v]}")]
    return []


def weak_hash_family(value: str) -> Optional[str]:
    return _WEAK_HASH.get(_norm(value).replace("_", "-"))
