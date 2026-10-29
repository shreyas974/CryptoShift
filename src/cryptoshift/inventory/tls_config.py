"""TLS configuration detector: nginx and Apache httpd TLS directives, and OpenSSL `openssl.cnf` settings.

Static analysis only: the effective suites/groups also depend on the OpenSSL build and the peer, so cipher-string
findings are reported with `medium` confidence. Private-key paths (`ssl_certificate_key`, `SSLCertificateKeyFile`)
are never opened.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

Detection = Tuple[str, str, str, str, str]  # family, purpose, ambiguity, confidence, reason

NGINX_RE = re.compile(
    r"^\s*((?:proxy_|grpc_|uwsgi_)?ssl_(?:protocols|ciphers|ecdh_curve|conf_command|certificate|dhparam))\s+(.*?)\s*;",
)
APACHE_RE = re.compile(
    r"^\s*(SSLProtocol|SSLProxyProtocol|SSLCipherSuite|SSLProxyCipherSuite|SSLOpenSSLConfCmd|SSLCertificateFile)\s+(.+?)\s*$",
    re.IGNORECASE,
)
OPENSSL_KV_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(.*?)\s*$")

OLD_PROTOCOLS = ("SSLv2", "SSLv3", "TLSv1", "TLSv1.1")
ALL_PROTOCOLS = ("SSLv3", "TLSv1", "TLSv1.1", "TLSv1.2", "TLSv1.3")
CIPHER_MACROS = {"HIGH", "MEDIUM", "LOW", "DEFAULT", "ALL", "COMPLEMENTOFDEFAULT", "COMPLEMENTOFALL",
                 "SECLEVEL", "@STRENGTH", "FIPS", "SUITEB128", "SUITEB192", "PROFILE=SYSTEM"}
RSA_KX_SUITE_PREFIXES = ("AES", "CAMELLIA", "DES-CBC3", "SEED", "RC4", "IDEA", "ARIA", "NULL-")
CLASSICAL_GROUPS = {"PRIME256V1", "SECP256R1", "SECP384R1", "SECP521R1", "P-256", "P-384", "P-521",
                    "X25519", "X448", "BRAINPOOLP256R1", "BRAINPOOLP384R1", "BRAINPOOLP512R1"}


def _strip_comment(line: str) -> str:
    return line.split("#", 1)[0] if "#" in line else line


def _unquote(v: str) -> str:
    v = v.strip()
    return v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"" else v


def analyse_cipher_string(value: str) -> List[Detection]:
    """Classify an OpenSSL/IANA cipher string into key-establishment, authentication and cipher families."""
    found: Dict[Tuple[str, str], str] = {}
    macro = False
    for tok in re.split(r"[:\s,]+", _unquote(value)):
        if not tok or tok[0] in "!-":
            continue
        up = tok.upper().lstrip("+").split("@", 1)[0]  # "DEFAULT@SECLEVEL=2" -> "DEFAULT"
        if not up or up in CIPHER_MACROS:
            macro = True
            continue
        parts = up.split("+")
        for p in parts:
            if p.startswith("TLS_"):  # IANA names
                if p.startswith(("TLS_ECDHE_", "TLS_ECDH_")):
                    found.setdefault(("ECDH", "key_establishment"), tok)
                elif p.startswith("TLS_DHE_"):
                    found.setdefault(("DH", "key_establishment"), tok)
                elif p.startswith("TLS_RSA_"):
                    found.setdefault(("RSA", "key_establishment"), tok)
                if "_RSA_WITH" in p and not p.startswith("TLS_RSA_"):
                    found.setdefault(("RSA", "digital_signature"), tok)
                if "_ECDSA_" in p:
                    found.setdefault(("ECDSA", "digital_signature"), tok)
                if "3DES" in p:
                    found.setdefault(("3DES", "symmetric_encryption"), tok)
                if "RC4" in p:
                    found.setdefault(("RC4", "symmetric_encryption"), tok)
                continue
            if p in ("ECDHE", "EECDH", "KECDHE", "ECDH", "KEECDH") or p.startswith(("ECDHE-", "ECDH-")):
                found.setdefault(("ECDH", "key_establishment"), tok)
            if p in ("DHE", "EDH", "KDHE", "KEDH") or p.startswith(("DHE-", "EDH-")):
                found.setdefault(("DH", "key_establishment"), tok)
            if p in ("KRSA", "RSA") or (p.startswith(RSA_KX_SUITE_PREFIXES) and "-" in p):
                found.setdefault(("RSA", "key_establishment"), tok)
            if p == "ARSA" or re.match(r"^(ECDHE|DHE|EDH)-RSA-", p):
                found.setdefault(("RSA", "digital_signature"), tok)
            if p in ("AECDSA", "ECDSA") or "-ECDSA-" in p:
                found.setdefault(("ECDSA", "digital_signature"), tok)
            if p in ("3DES", "DES-CBC3") or "DES-CBC3" in p:
                found.setdefault(("3DES", "symmetric_encryption"), tok)
            if p == "RC4" or p.startswith("RC4-") or "-RC4-" in p:
                found.setdefault(("RC4", "symmetric_encryption"), tok)

    reasons = {
        ("ECDH", "key_establishment"): "cipher string enables classical ECDHE key exchange",
        ("DH", "key_establishment"): "cipher string enables finite-field DHE key exchange",
        ("RSA", "key_establishment"): "cipher string enables static RSA key transport (no forward secrecy)",
        ("RSA", "digital_signature"): "cipher string enables RSA-authenticated suites (server certificate signature)",
        ("ECDSA", "digital_signature"): "cipher string enables ECDSA-authenticated suites",
        ("3DES", "symmetric_encryption"): "cipher string enables 3DES suites",
        ("RC4", "symmetric_encryption"): "cipher string enables RC4 suites",
    }
    out: List[Detection] = [
        (fam, purpose, "none", "medium", f"{reasons[(fam, purpose)]} (token '{tok}')")
        for (fam, purpose), tok in found.items()
    ]
    if not out and macro:
        out.append(("TLS-cipher-policy", "unknown", "ambiguous", "low",
                    "cipher string uses OpenSSL macros only; effective suites depend on the OpenSSL build"))
    return out


def analyse_groups(value: str) -> List[Detection]:
    toks = [t for t in re.split(r"[:\s,]+", _unquote(value)) if t]
    classical = [t for t in toks if t.upper() in CLASSICAL_GROUPS]
    ffdhe = [t for t in toks if t.lower().startswith("ffdhe")]
    hybrid = [t for t in toks if "MLKEM" in t.upper().replace("-", "") or "KYBER" in t.upper()]
    out: List[Detection] = []
    tail = f" alongside hybrid {', '.join(hybrid)} (classical fallback remains)" if hybrid else ""
    if classical:
        out.append(("ECDH", "key_establishment", "none", "high", f"classical key-exchange groups {', '.join(classical)}{tail}"))
    if ffdhe:
        out.append(("DH", "key_establishment", "none", "high", f"finite-field DH groups {', '.join(ffdhe)}{tail}"))
    if hybrid:
        out.append(("Hybrid-ML-KEM", "key_establishment", "none", "high", f"hybrid/PQC key-exchange group(s) {', '.join(hybrid)} configured"))
    return out


def analyse_protocols(value: str, apache_syntax: bool) -> List[Detection]:
    enabled: List[str] = []
    used_all = False
    for tok in _unquote(value).split():
        t = tok.strip()
        if apache_syntax and t.lower() in ("all", "+all"):
            enabled, used_all = list(ALL_PROTOCOLS), True
        elif t.startswith("-"):
            enabled = [p for p in enabled if p.lower() != t[1:].lower()]
        else:
            name = t.lstrip("+")
            norm = next((p for p in ALL_PROTOCOLS + ("SSLv2",) if p.lower() == name.lower()), name)
            if norm not in enabled:
                enabled.append(norm)
    old = [p for p in enabled if p in OLD_PROTOCOLS]
    conf = "medium" if used_all else "high"
    note = " ('all' semantics depend on the httpd/OpenSSL version)" if used_all else ""
    if old:
        return [("TLS-protocol", "transport_protocol", "none", conf, f"enables deprecated protocol(s) {', '.join(old)}{note}")]
    if "TLSv1.2" in enabled and "TLSv1.3" not in enabled:
        return [("TLS-protocol", "transport_protocol", "none", "medium",
                 "TLS 1.3 not enabled; hybrid ML-KEM key exchange requires TLS 1.3")]
    return []


def _cert_directive(value: str, config_path: Path, cert_inspector: Any) -> List[Detection]:
    raw = _unquote(value)
    cert_path = (config_path.parent / raw) if not Path(raw).is_absolute() else Path(raw)
    if cert_inspector is not None and cert_path.is_file():
        info = cert_inspector(cert_path)
        if info and info.get("family"):
            return [(info["family"], "digital_signature", info.get("ambiguity", "none"), "high",
                     f"referenced certificate public key: {info.get('summary', info['family'])}")]
    name = Path(raw).name.lower()
    if "rsa" in name:
        return [("RSA", "digital_signature", "none", "low", "certificate key type inferred from file name only (file not inspected)")]
    if "ecdsa" in name or "ecc" in name:
        return [("ECDSA", "digital_signature", "none", "low", "certificate key type inferred from file name only (file not inspected)")]
    return [("X.509-unknown-key", "digital_signature", "none", "low",
             "server certificate configured; key algorithm unknown (file not available to inspect)")]


def is_openssl_cnf(path: Path) -> bool:
    return path.name.lower() == "openssl.cnf" or path.suffix.lower() == ".cnf"


def scan_tls_config_text(text: str, path: Path, cert_inspector: Any = None) -> List[Dict[str, Any]]:
    """Return raw detection dicts for nginx/Apache/openssl.cnf text."""
    hits: List[Dict[str, Any]] = []
    openssl = is_openssl_cnf(path)
    for n, raw in enumerate(text.splitlines(), start=1):
        line = _strip_comment(raw)
        if not line.strip():
            continue
        detections: List[Detection] = []
        directive: Optional[str] = None
        value = ""
        server = "openssl.cnf"
        if openssl:
            m = OPENSSL_KV_RE.match(line)
            if not m:
                continue
            directive, value = m.group(1), m.group(2)
            key = directive.lower()
            if key == "cipherstring":
                detections = analyse_cipher_string(value)
            elif key in ("groups", "curves"):
                detections = analyse_groups(value)
            elif key == "minprotocol" and value.strip() in OLD_PROTOCOLS:
                detections = [("TLS-protocol", "transport_protocol", "none", "high", f"MinProtocol allows {value.strip()}")]
            elif key == "maxprotocol" and value.strip() in OLD_PROTOCOLS + ("TLSv1.2",):
                detections = [("TLS-protocol", "transport_protocol", "none", "high", f"MaxProtocol caps at {value.strip()} (no TLS 1.3)")]
            elif key == "default_md" and value.strip().lower() in ("sha1", "md5"):
                fam = "SHA-1" if value.strip().lower() == "sha1" else "MD5"
                detections = [(fam, "message_digest", "none", "high", f"default_md = {value.strip()} for signing")]
            elif key == "default_bits":
                detections = [("RSA", "digital_signature", "none", "medium", f"RSA key size {value.strip()} for generated certificate requests")]
            elif key in ("signaturealgorithms", "sigalgs"):
                v = value.upper()
                if "RSA" in v:
                    detections.append(("RSA", "digital_signature", "none", "high", "RSA signature algorithms allowed"))
                if "ECDSA" in v:
                    detections.append(("ECDSA", "digital_signature", "none", "high", "ECDSA signature algorithms allowed"))
        else:
            m = NGINX_RE.match(line)
            apache = False
            if not m:
                m = APACHE_RE.match(line)
                apache = bool(m)
            if not m:
                continue
            server = "apache" if apache else "nginx"
            directive, value = m.group(1), m.group(2)
            d = directive.lower()
            if d.endswith("ssl_protocols") or d in ("sslprotocol", "sslproxyprotocol"):
                detections = analyse_protocols(value, apache_syntax=apache)
            elif d.endswith("ssl_ciphers") or d in ("sslciphersuite", "sslproxyciphersuite"):
                v = _unquote(value)
                if apache and v.split()[0].upper() in ("TLSV1.3", "SSL"):
                    v = " ".join(v.split()[1:])
                detections = analyse_cipher_string(v)
            elif d.endswith("ssl_ecdh_curve"):
                detections = analyse_groups(value)
            elif d.endswith("ssl_conf_command") or d == "sslopensslconfcmd":
                parts = _unquote(value).split(None, 1)
                if len(parts) == 2:
                    sub, arg = parts[0].lower(), parts[1]
                    if sub in ("groups", "curves"):
                        detections = analyse_groups(arg)
                    elif sub == "cipherstring":
                        detections = analyse_cipher_string(arg)
                    elif sub == "minprotocol" and arg.strip() in OLD_PROTOCOLS:
                        detections = [("TLS-protocol", "transport_protocol", "none", "high", f"MinProtocol allows {arg.strip()}")]
            elif d.endswith("ssl_certificate") or d == "sslcertificatefile":
                detections = _cert_directive(value, path, cert_inspector)
            elif d.endswith("ssl_dhparam"):
                detections = [("DH", "key_establishment", "none", "high", "finite-field DHE parameters configured")]
        for fam, purpose, ambiguity, conf, reason in detections:
            hits.append({
                "line": n, "family": fam, "purpose": purpose, "ambiguity": ambiguity, "confidence": conf,
                "detected_value": f"{directive} {value.strip()}", "reason": f"{directive}: {reason}",
                "library_or_protocol": server,
                "snippet": raw, "location": f"directive {directive} (line {n})",
            })
    return hits


def looks_like_tls_config(text: str, path: Path) -> bool:
    if is_openssl_cnf(path):
        return True
    return any(NGINX_RE.match(_strip_comment(l)) or APACHE_RE.match(_strip_comment(l)) for l in text.splitlines())
