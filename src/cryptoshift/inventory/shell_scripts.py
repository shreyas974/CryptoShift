"""Shell-script and Dockerfile detector: `openssl` and `ssh-keygen` invocations with algorithm and size options.

A command counts only when `openssl` / `ssh-keygen` is the command word of a simple command (after `RUN`, `sudo`,
`exec`, `env` and VAR=value prefixes; commands split on ; && || |). `echo "openssl genrsa"`, comments, package
installs (`apt-get install openssl`) and `openssl version` / `rand` are not reported. Line continuations are joined
and the finding carries the first line. Purpose for SSH keys is digital_signature (they authenticate); openssl key
generation without context (genrsa, ecparam -genkey, genpkey RSA/EC) stays unknown and is flagged ambiguous.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cryptoshift.inventory.algorithm_ids import Detection, classify_identifier, is_pqc

VERSION = "shell_scripts/1.0"

SHELL_SUFFIXES = (".sh", ".bash", ".ksh", ".zsh")
PREFIX_WORDS = {"sudo", "exec", "env", "time", "nohup", "command", "then", "do", "else", "!"}
SPLIT_RE = re.compile(r"\s*(?:&&|\|\||;|\|)\s*")
SYM_ENC = {"-des3": "3DES", "-des": "DES", "-des-ede3": "3DES", "-des-ede3-cbc": "3DES", "-des-cbc": "DES", "-rc4": "RC4",
           "-bf": "Blowfish", "-bf-cbc": "Blowfish", "-rc2": "RC2", "-rc2-cbc": "RC2"}


def is_shell_or_dockerfile(path: Path) -> bool:
    n = path.name.lower()
    return path.suffix.lower() in SHELL_SUFFIXES or n == "dockerfile" or n.startswith("dockerfile.") or n.endswith(".dockerfile")


def _logical_lines(text: str, dockerfile: bool) -> List[Tuple[int, str]]:
    out: List[Tuple[int, str]] = []
    buf, start = "", 0
    for n, raw in enumerate(text.splitlines(), start=1):
        s = raw.rstrip()
        if not buf:
            start = n
            if s.lstrip().startswith("#"):
                continue
        if s.endswith("\\"):
            buf += s[:-1] + " "
            continue
        buf += s
        out.append((start, buf))
        buf = ""
    if buf:
        out.append((start, buf))
    if dockerfile:
        out = [(n, re.sub(r"^\s*RUN\s+", "", l, flags=re.I)) for n, l in out if re.match(r"^\s*RUN\s+", l, re.I)]
    return out


def _command_words(segment: str) -> Optional[List[str]]:
    try:
        toks = shlex.split(segment, comments=True, posix=True)
    except ValueError:
        return None
    while toks and (toks[0] in PREFIX_WORDS or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[0])):
        toks = toks[1:]
    return toks or None


def _opt(toks: List[str], name: str) -> Optional[str]:
    if name in toks:
        i = toks.index(name)
        return toks[i + 1] if i + 1 < len(toks) else None
    return None


def analyse_openssl(toks: List[str]) -> List[Detection]:
    if len(toks) < 2:
        return []
    sub, args = toks[1].lower(), toks[2:]
    out: List[Detection] = []
    low = [a.lower() for a in args]
    if sub == "genrsa":
        bits = next((a for a in args if a.isdigit()), "default size")
        out.append(("RSA", "unknown", "ambiguous", "high", f"openssl genrsa {bits}: RSA key generation; signing vs key transport not stated"))
    elif sub in ("req", "x509", "ca"):
        newkey = _opt(args, "-newkey")
        if newkey:
            alg = newkey.split(":", 1)[0]
            if is_pqc(alg):
                out.append(("ML-DSA", "digital_signature", "none", "high", f"openssl {sub} -newkey {newkey} (PQC)"))
            else:
                fam = {"rsa": "RSA", "ec": "ECDSA", "dsa": "DSA", "ed25519": "Ed25519", "ed448": "Ed448"}.get(alg.lower())
                if fam:
                    out.append((fam, "digital_signature", "none", "high", f"openssl {sub} -newkey {newkey}: certificate/CSR key ({fam} signature)"))
        for h in ("-sha1", "-md5"):
            if h in low:
                out.append(("SHA-1" if h == "-sha1" else "MD5", "message_digest", "none", "high", f"openssl {sub} {h}: weak signature digest"))
    elif sub == "genpkey":
        alg = _opt(args, "-algorithm") or ""
        bits = next((a.split(":", 1)[1] for a in args if a.startswith(("rsa_keygen_bits:", "ec_paramgen_curve:", "group:"))), "")
        dets = classify_identifier(alg)
        out += [(f, p, a, "high", f"openssl genpkey -algorithm {alg} {bits}".strip() + f": {r}") for f, p, a, _c, r in dets]
    elif sub == "ecparam" and "-genkey" in low:
        out.append(("EC", "unknown", "ambiguous", "high", f"openssl ecparam -genkey -name {_opt(args, '-name') or '?'}: EC key; ECDSA vs ECDH not stated"))
    elif sub == "dhparam":
        out.append(("DH", "key_establishment", "none", "high", "openssl dhparam: finite-field DH parameters"))
    elif sub in ("gendsa", "dsaparam"):
        out.append(("DSA", "digital_signature", "none", "high", f"openssl {sub}: DSA (signature-only)"))
    elif sub == "dgst":
        for h, fam in (("-sha1", "SHA-1"), ("-md5", "MD5")):
            if h in low:
                out.append((fam, "message_digest", "none", "high", f"openssl dgst {h}"))
    elif sub == "enc":
        for a in low:
            if a in SYM_ENC:
                out.append((SYM_ENC[a], "symmetric_encryption", "none", "high", f"openssl enc {a}"))
    elif sub == "rsautl":
        if "-encrypt" in low or "-decrypt" in low:
            out.append(("RSA", "key_establishment", "none", "high", "openssl rsautl -encrypt/-decrypt: RSA encryption"))
        if "-sign" in low or "-verify" in low:
            out.append(("RSA", "digital_signature", "none", "high", "openssl rsautl -sign/-verify: RSA signature"))
    elif sub in ("s_client", "s_server"):
        for flag, ver in (("-ssl3", "SSLv3"), ("-tls1", "TLSv1"), ("-tls1_1", "TLSv1.1")):
            if flag in low:
                out.append(("TLS-protocol", "transport_protocol", "none", "high", f"openssl {sub} {flag} ({ver})"))
    return out


def analyse_ssh_keygen(toks: List[str]) -> List[Detection]:
    t = _opt(toks, "-t")
    if not t:
        return []
    bits = _opt(toks, "-b")
    size = f" -b {bits}" if bits else ""
    fam = {"rsa": "RSA", "dsa": "DSA", "ecdsa": "ECDSA", "ed25519": "Ed25519", "rsa1": "RSA"}.get(t.lower())
    if not fam:
        return []
    return [(fam, "digital_signature", "none", "high", f"ssh-keygen -t {t}{size}: SSH key ({fam} authentication signatures)")]


SECRET_FLAGS = {"-pass", "-passin", "-passout", "-k", "-kfile", "-n", "-p", "-password", "-passphrase", "-key", "-inkey",
                "-signkey", "-out", "-keyout", "-f"}


def redact_command(toks: List[str]) -> str:
    """Command text without passphrases or key/output paths (values after secret-bearing flags are masked)."""
    out: List[str] = []
    mask_next = False
    for t in toks:
        if mask_next:
            out.append("[REDACTED]")
            mask_next = False
            continue
        if t.lower() in SECRET_FLAGS or t == "-N" or t == "-P":
            mask_next = True
            out.append(t)
            continue
        if re.match(r"^(pass|env|file|fd):", t, re.I):
            out.append("[REDACTED]")
            continue
        out.append(t)
    return " ".join(out)[:200]


def scan_shell_text(text: str, path: Path) -> List[Dict[str, Any]]:
    dockerfile = not path.suffix.lower() in SHELL_SUFFIXES
    lines = text.splitlines()
    hits: List[Dict[str, Any]] = []
    seen = set()
    for n, logical in _logical_lines(text, dockerfile):
        for seg in SPLIT_RE.split(logical):
            seg = re.sub(r"^\s*(?:if|while|until)\s+", "", seg.strip().lstrip("(").strip())
            toks = _command_words(seg)
            if not toks:
                continue
            cmd = Path(toks[0]).name.lower().removesuffix(".exe")
            if cmd == "openssl":
                dets, tool = analyse_openssl(toks), "openssl"
            elif cmd == "ssh-keygen":
                dets, tool = analyse_ssh_keygen(toks), "ssh-keygen"
            else:
                continue
            for fam, purpose, ambiguity, conf, reason in dets:
                if (n, fam, purpose) in seen:
                    continue
                seen.add((n, fam, purpose))
                hits.append({
                    "line": n, "family": fam, "purpose": purpose, "ambiguity": ambiguity, "confidence": conf,
                    "detected_value": redact_command(toks), "reason": reason, "library_or_protocol": tool,
                    "snippet": redact_command(_command_words(lines[n - 1].split("#", 1)[0]) or []) if 0 < n <= len(lines) else "",
                    "location": f"{tool} command (line {n})",
                })
    return hits
