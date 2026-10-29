"""Dependency-manifest detector: requirements*.txt, package.json and Maven pom.xml.

A dependency only shows that a crypto-capable library is present, not how it is used, so most findings are
`low` confidence with `ambiguity="unknown"` (purpose cannot be determined from a manifest).
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

# name -> (family, purpose, ambiguity, confidence, reason)
LibRule = Tuple[str, str, str, str, str]

PYPI_LIBS: Dict[str, LibRule] = {
    "cryptography": ("crypto-library", "unknown", "unknown", "low", "general-purpose library exposing RSA/EC/DH/DSA"),
    "pycryptodome": ("crypto-library", "unknown", "unknown", "low", "general-purpose library exposing RSA/ECC/DSA/3DES"),
    "pycryptodomex": ("crypto-library", "unknown", "unknown", "low", "general-purpose library exposing RSA/ECC/DSA/3DES"),
    "pycrypto": ("crypto-library", "unknown", "unknown", "low", "unmaintained library exposing RSA/DSA/DES"),
    "pyopenssl": ("crypto-library", "unknown", "unknown", "low", "OpenSSL bindings (TLS, X.509, RSA/EC)"),
    "m2crypto": ("crypto-library", "unknown", "unknown", "low", "OpenSSL bindings (TLS, X.509, RSA/EC)"),
    "rsa": ("RSA", "unknown", "unknown", "low", "pure-Python RSA library (signing or encryption)"),
    "ecdsa": ("ECDSA", "digital_signature", "none", "low", "pure-Python ECDSA signature library"),
    "pyjwt": ("JWT", "unknown", "unknown", "low", "JWT library; RS/ES/PS algorithms use RSA/ECDSA signatures"),
    "python-jose": ("JWT", "unknown", "unknown", "low", "JOSE library; RSA/EC signatures and RSA-OAEP key wrap"),
    "jwcrypto": ("JWT", "unknown", "unknown", "low", "JOSE library; RSA/EC signatures and key wrap"),
    "authlib": ("JWT", "unknown", "unknown", "low", "OAuth/JOSE library; RSA/EC signatures"),
    "paramiko": ("SSH", "unknown", "unknown", "low", "SSH library (RSA/ECDSA host keys, DH/ECDH key exchange)"),
    "pynacl": ("X25519/Ed25519", "unknown", "unknown", "low", "libsodium bindings (X25519 key exchange, Ed25519 signatures)"),
    "tlslite-ng": ("TLS-library", "unknown", "unknown", "low", "pure-Python TLS implementation"),
    "liboqs-python": ("ML-KEM", "key_establishment", "none", "low", "Open Quantum Safe bindings (PQC algorithms present)"),
}
NPM_LIBS: Dict[str, LibRule] = {
    "node-rsa": ("RSA", "unknown", "unknown", "low", "RSA library (encryption or signing)"),
    "jsonwebtoken": ("JWT", "unknown", "unknown", "low", "JWT library; RS/ES/PS algorithms use RSA/ECDSA signatures"),
    "jose": ("JWT", "unknown", "unknown", "low", "JOSE library; RSA/EC signatures and key wrap"),
    "jsrsasign": ("JWT", "unknown", "unknown", "low", "RSA/ECDSA signing library"),
    "elliptic": ("EC", "unknown", "unknown", "low", "elliptic-curve library (ECDSA/ECDH)"),
    "node-forge": ("crypto-library", "unknown", "unknown", "low", "general-purpose library (RSA, X.509, TLS, 3DES)"),
    "crypto-js": ("crypto-library", "unknown", "unknown", "low", "symmetric/hash library (includes 3DES, MD5, SHA-1)"),
    "tweetnacl": ("X25519/Ed25519", "unknown", "unknown", "low", "X25519 key exchange and Ed25519 signatures"),
    "@noble/curves": ("EC", "unknown", "unknown", "low", "elliptic-curve library (ECDSA/ECDH/EdDSA)"),
    "ssh2": ("SSH", "unknown", "unknown", "low", "SSH library (RSA/ECDSA keys, DH/ECDH key exchange)"),
    "openpgp": ("crypto-library", "unknown", "unknown", "low", "OpenPGP (RSA/ECC encryption and signatures)"),
}
MAVEN_LIBS: Dict[str, LibRule] = {
    "org.bouncycastle:": ("crypto-library", "unknown", "unknown", "low", "Bouncy Castle provider (RSA/EC/DH and PQC)"),
    "io.jsonwebtoken:": ("JWT", "unknown", "unknown", "low", "JJWT library; RS/ES/PS algorithms use RSA/ECDSA signatures"),
    "com.nimbusds:nimbus-jose-jwt": ("JWT", "unknown", "unknown", "low", "JOSE library; RSA/EC signatures and key wrap"),
    "com.auth0:java-jwt": ("JWT", "unknown", "unknown", "low", "JWT library; RSA/ECDSA signatures"),
    "org.apache.santuario:xmlsec": ("XMLDSig", "digital_signature", "none", "low", "XML signature library (RSA/ECDSA signatures)"),
    "com.jcraft:jsch": ("SSH", "unknown", "unknown", "low", "SSH library (RSA/DSA keys, DH key exchange)"),
    "com.github.mwiede:jsch": ("SSH", "unknown", "unknown", "low", "SSH library (RSA/ECDSA keys, DH/ECDH key exchange)"),
}

REQ_LINE_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*([^;#]*)")


def _norm_pypi(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _hit(line: int, rule: LibRule, spec: str, kind: str, raw: str) -> Dict[str, Any]:
    fam, purpose, ambiguity, conf, reason = rule
    return {
        "line": line, "family": fam, "purpose": purpose, "ambiguity": ambiguity, "confidence": conf,
        "detected_value": spec, "reason": f"{kind} dependency '{spec}': {reason}; usage not determined from manifest",
        "library_or_protocol": spec.split("==")[0].split("@")[0], "snippet": raw, "location": f"line {line}",
    }


def scan_requirements(text: str) -> List[Dict[str, Any]]:
    hits = []
    for n, raw in enumerate(text.splitlines(), start=1):
        s = raw.strip()
        if not s or s.startswith(("#", "-", "--")):
            continue
        m = REQ_LINE_RE.match(s)
        if not m:
            continue
        name = _norm_pypi(m.group(1))
        rule = PYPI_LIBS.get(name)
        if rule:
            hits.append(_hit(n, rule, f"{m.group(1)}{m.group(2) or ''}{m.group(3).strip()}", "PyPI", raw))
    return hits


def scan_package_json(text: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads(text)
    except ValueError:
        return []
    lines = text.splitlines()
    hits = []
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        deps = data.get(section) or {}
        if not isinstance(deps, dict):
            continue
        for name, ver in deps.items():
            rule = NPM_LIBS.get(name)
            if not rule:
                continue
            line = next((i for i, l in enumerate(lines, start=1) if f'"{name}"' in l), 0)
            hits.append(_hit(line, rule, f"{name}@{ver}", f"npm ({section})", lines[line - 1] if line else ""))
    return hits


def _maven_rule(group: str, artifact: str) -> Optional[LibRule]:
    full = f"{group}:{artifact}"
    for key, rule in MAVEN_LIBS.items():
        if (key.endswith(":") and full.startswith(key)) or full == key:
            return rule
    return None


def scan_pom(text: str) -> List[Dict[str, Any]]:
    if len(text) > 2_000_000 or "<!ENTITY" in text:
        return []  # refuse oversized or entity-declaring XML
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    ns = {"m": root.tag[1:].split("}")[0]} if root.tag.startswith("{") else {}
    q = (lambda t: f"m:{t}") if ns else (lambda t: t)
    lines = text.splitlines()
    hits = []
    for dep in root.iter(f"{{{ns['m']}}}dependency" if ns else "dependency"):
        g = dep.findtext(q("groupId"), default="", namespaces=ns).strip()
        a = dep.findtext(q("artifactId"), default="", namespaces=ns).strip()
        v = dep.findtext(q("version"), default="", namespaces=ns).strip()
        rule = _maven_rule(g, a)
        if not rule:
            continue
        line = next((i for i, l in enumerate(lines, start=1) if f"<artifactId>{a}</artifactId>" in l), 0)
        hits.append(_hit(line, rule, f"{g}:{a}:{v}" if v else f"{g}:{a}", "Maven", lines[line - 1] if line else ""))
    return hits


def manifest_kind(name: str) -> Optional[str]:
    n = name.lower()
    if n.startswith("requirements") and n.endswith(".txt"):
        return "requirements"
    if n == "package.json":
        return "package.json"
    if n == "pom.xml":
        return "pom.xml"
    return None


def scan_manifest_text(text: str, name: str) -> List[Dict[str, Any]]:
    kind = manifest_kind(name)
    if kind == "requirements":
        return scan_requirements(text)
    if kind == "package.json":
        return scan_package_json(text)
    if kind == "pom.xml":
        return scan_pom(text)
    return []
