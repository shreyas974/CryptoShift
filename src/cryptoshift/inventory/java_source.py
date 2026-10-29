"""Java source detector (LIMITED SCOPE): JCA `getInstance(...)` calls with a visible algorithm name.

What it does:
- tokenises Java with comment and string awareness (// and /* */ comments, "..." strings, text blocks, char literals),
  so algorithm names inside comments are never matched;
- resolves the class through imports: `Cipher` counts only if `javax.crypto.Cipher` (or `javax.crypto.*`) is imported,
  or the call is fully qualified; a class declared in the same file with the same name shadows it;
- covers Cipher, KeyPairGenerator, Signature, KeyAgreement, MessageDigest, SSLContext and KeyStore;
- reads the first argument when it is a string literal, or a String constant assigned once in the same file.

What it does NOT do: no data flow across methods or files, no Bouncy Castle lightweight API, no Kotlin/Scala, no
reflection, no key sizes passed to `initialize(...)`, no default-provider semantics beyond "AES" = AES/ECB.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from cryptoshift.inventory.algorithm_ids import Detection, classify_identifier, is_pqc

VERSION = "java_source/1.0 (limited scope)"

JCA_CLASSES = {
    "Cipher": "javax.crypto", "KeyAgreement": "javax.crypto", "KeyPairGenerator": "java.security",
    "Signature": "java.security", "MessageDigest": "java.security", "KeyStore": "java.security",
    "SSLContext": "javax.net.ssl",
}

Token = Tuple[str, str, int]  # kind (ident|string|punct|number), value, line


def tokenize(src: str) -> List[Token]:
    toks: List[Token] = []
    i, line, n = 0, 1, len(src)
    while i < n:
        c = src[i]
        if c == "\n":
            line += 1; i += 1; continue
        if c in " \t\r\f":
            i += 1; continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            line += src.count("\n", i, j)
            i = j
            continue
        if src.startswith('"""', i):
            j = src.find('"""', i + 3)
            j = n if j < 0 else j + 3
            toks.append(("string", src[i + 3:j - 3], line))
            line += src.count("\n", i, j)
            i = j
            continue
        if c == '"':
            j, buf = i + 1, []
            while j < n and src[j] != '"' and src[j] != "\n":
                if src[j] == "\\" and j + 1 < n:
                    buf.append(src[j + 1]); j += 2; continue
                buf.append(src[j]); j += 1
            toks.append(("string", "".join(buf), line))
            i = j + 1
            continue
        if c == "'":
            j = i + 1
            while j < n and src[j] != "'" and src[j] != "\n":
                j += 2 if src[j] == "\\" else 1
            i = j + 1
            continue
        if c.isalpha() or c in "_$":
            j = i + 1
            while j < n and (src[j].isalnum() or src[j] in "_$"):
                j += 1
            toks.append(("ident", src[i:j], line))
            i = j
            continue
        if c.isdigit():
            j = i + 1
            while j < n and (src[j].isalnum() or src[j] in "._"):
                j += 1
            toks.append(("number", src[i:j], line))
            i = j
            continue
        toks.append(("punct", c, line))
        i += 1
    return toks


def _imports(toks: List[Token]) -> Tuple[Dict[str, str], List[str], set]:
    explicit: Dict[str, str] = {}
    wildcard: List[str] = []
    declared: set = set()
    i = 0
    while i < len(toks):
        kind, val, _ = toks[i]
        if kind == "ident" and val == "import":
            j, parts = i + 1, []
            if j < len(toks) and toks[j][1] == "static":
                while j < len(toks) and toks[j][1] != ";":
                    j += 1
                i = j + 1
                continue
            while j < len(toks) and toks[j][1] != ";":
                if toks[j][0] == "ident" or toks[j][1] == "*":
                    parts.append(toks[j][1])
                j += 1
            if parts and parts[-1] == "*":
                wildcard.append(".".join(parts[:-1]))
            elif parts:
                explicit[parts[-1]] = ".".join(parts[:-1])
            i = j + 1
            continue
        if kind == "ident" and val in ("class", "interface", "enum", "record") and i + 1 < len(toks) and toks[i + 1][0] == "ident":
            declared.add(toks[i + 1][1])
        i += 1
    return explicit, wildcard, declared


def _string_constants(toks: List[Token]) -> Dict[str, Tuple[str, int]]:
    """NAME -> (value, line) for `NAME = "literal" ;` assigned exactly once in the file."""
    seen: Dict[str, List[Tuple[str, int]]] = {}
    for i in range(len(toks) - 3):
        a, b, c, d = toks[i:i + 4]
        if a[0] == "ident" and b[1] == "=" and c[0] == "string" and d[1] in (";", ","):
            if i > 0 and toks[i - 1][1] in ("=", "!", "<", ">"):
                continue
            seen.setdefault(a[1], []).append((c[1], c[2]))
    return {k: v[0] for k, v in seen.items() if len(v) == 1}


def classify_jca(cls: str, alg: str) -> List[Detection]:
    a = alg.strip()
    up = a.upper()
    if not a:
        return []
    if is_pqc(a):
        return classify_identifier(a)
    if cls == "Cipher":
        parts = up.split("/")
        base, mode = parts[0], parts[1] if len(parts) > 1 else ""
        if base == "RSA":
            pad = parts[2] if len(parts) > 2 else ""
            note = "OAEP" if "OAEP" in pad else pad or "default padding"
            return [("RSA", "key_establishment", "none", "high", f"Cipher {a}: RSA encryption / key transport ({note})")]
        if base in ("ECIES",):
            return [("ECDH", "key_establishment", "none", "high", f"Cipher {a}: ECIES")]
        if base.startswith("PBEWITHMD5AND") or base.startswith("PBEWITHSHA1AND"):
            out: List[Detection] = [("MD5" if "MD5" in base else "SHA-1", "message_digest", "none", "high", f"Cipher {a}: weak PBE digest")]
            if "DES" in base:
                out.append(("3DES" if "TRIPLEDES" in base or "DESEDE" in base else "DES", "symmetric_encryption", "none", "high", f"Cipher {a}"))
            return out
        if base in ("AES", "AES_128", "AES_256") and (mode in ("", "ECB")):
            why = "AES with ECB mode" if mode == "ECB" else "AES without mode (provider default is ECB)"
            return [("AES-ECB", "symmetric_encryption", "none", "high" if mode else "medium", f"Cipher {a}: {why}")]
        if base in ("RC2",):
            return [("RC2", "symmetric_encryption", "none", "high", f"Cipher {a}: RC2")]
        return [d for d in classify_identifier(base) if d[1] == "symmetric_encryption"]
    if cls == "KeyPairGenerator":
        if up in ("RSA", "EC", "DSA", "DH", "DIFFIEHELLMAN", "X25519", "X448", "XDH", "ED25519", "ED448", "EDDSA", "RSASSA-PSS"):
            if up == "RSASSA-PSS":
                return [("RSA", "digital_signature", "none", "high", "KeyPairGenerator RSASSA-PSS")]
            return [(f, p, amb, "high", f"KeyPairGenerator {a}: {r}") for f, p, amb, _c, r in classify_identifier(up)]
        return []
    if cls == "Signature":
        return [(f, p, amb, "high", f"Signature {a}: {r}") for f, p, amb, _c, r in classify_identifier(up)]
    if cls == "KeyAgreement":
        fam = {"ECDH": "ECDH", "DH": "DH", "DIFFIEHELLMAN": "DH", "X25519": "X25519", "X448": "X448", "XDH": "X25519", "ECMQV": "ECDH"}.get(up)
        return [(fam, "key_establishment", "none", "high", f"KeyAgreement {a}")] if fam else []
    if cls == "MessageDigest":
        fam = {"MD5": "MD5", "MD2": "MD2", "MD4": "MD4", "SHA1": "SHA-1", "SHA-1": "SHA-1", "SHA": "SHA-1"}.get(up)
        return [(fam, "message_digest", "none", "high", f"MessageDigest {a}")] if fam else []
    if cls == "SSLContext":
        if up in ("SSL", "SSLV2", "SSLV3", "TLSV1", "TLSV1.1"):
            return [("TLS-protocol", "transport_protocol", "none", "high", f"SSLContext {a}: deprecated protocol")]
        if up == "TLSV1.2":
            return [("TLS-protocol", "transport_protocol", "none", "medium", "SSLContext TLSv1.2: TLS 1.3 not requested (hybrid ML-KEM needs TLS 1.3)")]
        return []
    if cls == "KeyStore":
        if up in ("JKS", "JCEKS"):
            return [("KeyStore", "unknown", "unknown", "low", f"KeyStore {a}: legacy key store format; contained key algorithms are not visible statically")]
        return []
    return []


def _resolve_class(toks: List[Token], i: int, explicit: Dict[str, str], wildcard: List[str], declared: set) -> Optional[str]:
    """toks[i] is the class name before `.getInstance`; return the JCA simple name if it resolves to the JCA class."""
    name = toks[i][1]
    if name not in JCA_CLASSES:
        return None
    pkg = JCA_CLASSES[name]
    # fully qualified: javax . crypto . Cipher
    qual: List[str] = []
    j = i - 1
    while j >= 1 and toks[j][1] == "." and toks[j - 1][0] == "ident":
        qual.insert(0, toks[j - 1][1])
        j -= 2
    if qual:
        return name if ".".join(qual) == pkg else None
    if name in declared:
        return None
    if explicit.get(name) == pkg or pkg in wildcard:
        return name
    return None


def scan_java_source(text: str) -> List[Dict[str, Any]]:
    toks = tokenize(text)
    explicit, wildcard, declared = _imports(toks)
    consts = _string_constants(toks)
    lines = text.splitlines()
    hits: List[Dict[str, Any]] = []
    seen = set()
    for i in range(len(toks) - 4):
        if not (toks[i][0] == "ident" and toks[i + 1][1] == "." and toks[i + 2][1] == "getInstance" and toks[i + 3][1] == "("):
            continue
        cls = _resolve_class(toks, i, explicit, wildcard, declared)
        if not cls:
            continue
        arg = toks[i + 4]
        nxt = toks[i + 5][1] if i + 5 < len(toks) else ""
        if nxt not in (")", ","):
            continue  # expression (concatenation, method call): not resolved
        conf_note = ""
        if arg[0] == "string":
            alg = arg[1]
        elif arg[0] == "ident" and arg[1] in consts:
            alg, cline = consts[arg[1]]
            conf_note = f" (value from constant {arg[1]} at line {cline})"
        else:
            continue
        line = toks[i][2]
        for fam, purpose, ambiguity, conf, reason in classify_jca(cls, alg):
            if (line, fam, purpose) in seen:
                continue
            seen.add((line, fam, purpose))
            hits.append({
                "line": line, "family": fam, "purpose": purpose, "ambiguity": ambiguity,
                "confidence": "medium" if conf_note and conf == "high" else conf,
                "detected_value": f"{cls}.getInstance(\"{alg}\")", "reason": reason + conf_note,
                "library_or_protocol": "java-jca", "snippet": lines[line - 1] if 0 < line <= len(lines) else "",
            })
    return hits
