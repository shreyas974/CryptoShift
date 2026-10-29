"""Certificate-file detector: reports public-key algorithm, key size, signature hash and expiry ONLY.

Never emits subjects, issuers, serials, extensions' contents, PEM bodies or private-key material. A file that
contains a private key is reported as "private key material present" without being parsed.
Requires the `cryptography` package; if it is missing the detector reports itself as unavailable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

CERT_SUFFIXES = (".crt", ".cer", ".pem", ".der")
MAX_CERT_BYTES = 1_000_000


def certificate_parser_available() -> bool:
    try:
        import cryptography.x509  # noqa: F401
    except ImportError:
        return False
    return True


def _describe(cert: Any) -> Dict[str, Any]:
    from cryptography import x509
    from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed448, ed25519, rsa

    pk = cert.public_key()
    if isinstance(pk, rsa.RSAPublicKey):
        family, size, label = "RSA", pk.key_size, f"RSA-{pk.key_size}"
    elif isinstance(pk, ec.EllipticCurvePublicKey):
        family, size, label = "ECDSA", pk.key_size, f"EC-{pk.curve.name}"
    elif isinstance(pk, ed25519.Ed25519PublicKey):
        family, size, label = "Ed25519", 256, "Ed25519"
    elif isinstance(pk, ed448.Ed448PublicKey):
        family, size, label = "Ed448", 456, "Ed448"
    elif isinstance(pk, dsa.DSAPublicKey):
        family, size, label = "DSA", pk.key_size, f"DSA-{pk.key_size}"
    else:
        family, size, label = "unknown-public-key", None, type(pk).__name__

    try:
        sig_hash = cert.signature_hash_algorithm.name if cert.signature_hash_algorithm else None
    except Exception:  # e.g. unsupported algorithm
        sig_hash = None
    not_after = cert.not_valid_after_utc

    ambiguity = "none"
    try:
        ku = cert.extensions.get_extension_for_class(x509.KeyUsage).value
        if family == "RSA" and ku.key_encipherment and ku.digital_signature:
            ambiguity = "ambiguous"  # RSA key may be used for signatures and (TLS 1.2) key transport
    except x509.ExtensionNotFound:
        pass

    return {
        "family": family,
        "algorithm_label": label,
        "key_size": size,
        "signature_hash": sig_hash,
        "not_valid_after_utc": not_after.isoformat(),
        "expired": not_after < datetime.now(timezone.utc),
        "ambiguity": ambiguity,
        "summary": f"{label}, signature hash {sig_hash or 'n/a'}, expires {not_after.date().isoformat()}",
    }


def inspect_certificate_file(path: Path) -> Optional[Dict[str, Any]]:
    """Return metadata for the first certificate in `path`, or a private-key marker, or None."""
    infos = inspect_certificate_bytes(path.read_bytes()[:MAX_CERT_BYTES]) if path.stat().st_size <= MAX_CERT_BYTES else []
    return infos[0] if infos else None


def inspect_certificate_bytes(data: bytes) -> List[Dict[str, Any]]:
    if b"PRIVATE KEY-----" in data:
        kind = "RSA" if b"BEGIN RSA PRIVATE KEY" in data else "EC" if b"BEGIN EC PRIVATE KEY" in data else "unknown"
        return [{"family": kind, "private_key_material": True, "ambiguity": "unknown",
                 "summary": "private key material present (not parsed, not reported)"}]
    if not certificate_parser_available():
        return []
    from cryptography import x509

    try:
        if b"-----BEGIN CERTIFICATE-----" in data:
            certs = x509.load_pem_x509_certificates(data)
        else:
            certs = [x509.load_der_x509_certificate(data)]
    except ValueError:
        return []
    return [_describe(c) for c in certs]


def scan_certificate_file(path: Path) -> List[Dict[str, Any]]:
    """Raw detection dicts (one per certificate) for a certificate-like file."""
    if path.stat().st_size > MAX_CERT_BYTES:
        return []
    infos = inspect_certificate_bytes(path.read_bytes())
    hits: List[Dict[str, Any]] = []
    for i, info in enumerate(infos, start=1):
        if info.get("private_key_material"):
            hits.append({
                "line": 0, "family": info["family"], "purpose": "unknown", "ambiguity": "unknown", "confidence": "high",
                "detected_value": "private key file", "location": "file",
                "reason": "File contains private key material; contents were not parsed or reported. Check it is not committed.",
                "library_or_protocol": "PEM", "snippet": "",
            })
            continue
        expired = " (EXPIRED)" if info["expired"] else ""
        hits.append({
            "line": 0, "family": info["family"], "purpose": "digital_signature", "ambiguity": info["ambiguity"],
            "confidence": "high", "algorithm_label": info["algorithm_label"],
            "detected_value": info["summary"] + expired, "location": f"certificate #{i}",
            "reason": f"X.509 certificate public key {info['algorithm_label']}; "
                      f"signature hash {info['signature_hash'] or 'n/a'}; not after {info['not_valid_after_utc']}{expired}"
                      + ("; KeyUsage allows both signatures and key encipherment" if info["ambiguity"] == "ambiguous" else ""),
            "library_or_protocol": "X.509", "snippet": "",
        })
    return hits
