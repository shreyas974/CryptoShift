"""HAProxy TLS detector: global `ssl-default-*` directives and `bind` / `server` line options.

Covers ciphers (TLS <= 1.2 cipher strings), ciphersuites (TLS 1.3), curves / ecdhe, ssl-min-ver / ssl-max-ver,
no-tlsv13 / force-tlsvXX options, DH parameters, and the `crt` certificate (key type inferred only when the file can be
inspected, otherwise from its name with low confidence). Private-key files are never opened.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any, Dict, List

from cryptoshift.inventory.algorithm_ids import Detection
from cryptoshift.inventory.tls_config import OLD_PROTOCOLS, _cert_directive, analyse_cipher_string, analyse_groups

VERSION = "haproxy/1.0"

SECTION_RE = re.compile(r"^\s*(global|defaults|frontend|backend|listen)\b", re.I)
_VER = {"SSLV3": "SSLv3", "TLSV10": "TLSv1", "TLSV11": "TLSv1.1", "TLSV12": "TLSv1.2", "TLSV13": "TLSv1.3"}


def looks_like_haproxy(text: str, path: Path) -> bool:
    if "haproxy" in path.name.lower():
        return True
    if path.suffix.lower() != ".cfg":
        return False
    lines = text.splitlines()
    return any(SECTION_RE.match(l) for l in lines) and any(l.strip().startswith(("bind ", "server ", "ssl-default-")) for l in lines)


def _min_ver(v: str) -> List[Detection]:
    ver = _VER.get(v.upper().replace(".", ""), v)
    if ver in OLD_PROTOCOLS:
        return [("TLS-protocol", "transport_protocol", "none", "high", f"minimum TLS version {ver} allows deprecated protocols")]
    return []


def _max_ver(v: str) -> List[Detection]:
    ver = _VER.get(v.upper().replace(".", ""), v)
    if ver in OLD_PROTOCOLS + ("TLSv1.2",):
        return [("TLS-protocol", "transport_protocol", "none", "high", f"maximum TLS version {ver} (no TLS 1.3, so no hybrid ML-KEM groups)")]
    return []


def analyse_options(tokens: List[str], path: Path, cert_inspector: Any) -> List[Detection]:
    out: List[Detection] = []
    i = 0
    while i < len(tokens):
        t = tokens[i].lower()
        arg = tokens[i + 1] if i + 1 < len(tokens) else ""
        if t == "ciphers":
            out += analyse_cipher_string(arg); i += 2; continue
        if t in ("curves", "ecdhe"):
            out += analyse_groups(arg); i += 2; continue
        if t == "ssl-min-ver":
            out += _min_ver(arg); i += 2; continue
        if t == "ssl-max-ver":
            out += _max_ver(arg); i += 2; continue
        if t == "crt" and arg:
            out += _cert_directive(arg, path, cert_inspector); i += 2; continue
        if t == "no-tlsv13":
            out.append(("TLS-protocol", "transport_protocol", "none", "high", "no-tlsv13 disables TLS 1.3 (no hybrid ML-KEM groups)"))
        elif t in ("force-sslv3", "force-tlsv10", "force-tlsv11"):
            out.append(("TLS-protocol", "transport_protocol", "none", "high", f"{t} forces a deprecated protocol"))
        elif t == "force-tlsv12":
            out.append(("TLS-protocol", "transport_protocol", "none", "high", "force-tlsv12 pins TLS 1.2 (no TLS 1.3)"))
        i += 1
    return out


def scan_haproxy_text(text: str, path: Path, cert_inspector: Any = None) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    seen = set()
    for n, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        try:
            toks = shlex.split(line, posix=True)
        except ValueError:
            toks = line.split()
        if not toks:
            continue
        d = toks[0].lower()
        detections: List[Detection] = []
        if d in ("ssl-default-bind-ciphers", "ssl-default-server-ciphers") and len(toks) > 1:
            detections = analyse_cipher_string(toks[1])
        elif d in ("ssl-default-bind-curves", "ssl-default-server-curves") and len(toks) > 1:
            detections = analyse_groups(toks[1])
        elif d in ("ssl-default-bind-options", "ssl-default-server-options"):
            detections = analyse_options(toks[1:], path, cert_inspector)
        elif d in ("ssl-dh-param-file", "tune.ssl.default-dh-param"):
            detections = [("DH", "key_establishment", "none", "high", f"{d}: finite-field DHE parameters configured")]
        elif d in ("bind", "server", "default-server") and any(t.lower() in ("ssl", "crt", "ciphers", "ssl-min-ver") for t in toks):
            detections = analyse_options(toks[1:], path, cert_inspector)
        for fam, purpose, ambiguity, conf, reason in detections:
            if (n, fam, purpose) in seen:
                continue
            seen.add((n, fam, purpose))
            hits.append({
                "line": n, "family": fam, "purpose": purpose, "ambiguity": ambiguity, "confidence": conf,
                "detected_value": line[:200], "reason": f"haproxy {toks[0]}: {reason}", "library_or_protocol": "haproxy",
                "snippet": raw, "location": f"haproxy {toks[0]} (line {n})",
            })
    return hits
