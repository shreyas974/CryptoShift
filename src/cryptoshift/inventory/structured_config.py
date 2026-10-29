"""Structured-config detector: YAML, Java .properties / java.security, and JSON TLS and crypto settings.

Only keys whose name carries a crypto keyword (cipher, protocol, group, curve, algorithm, signature, digest, ...)
are inspected, and only exact identifiers from the shared vocabulary are reported. Values under keys that DISABLE
something (`disabled`, `exclude`, `deny`, ...) are never reported as enabled; `jdk.tls.disabledAlgorithms` is
checked the other way round (which deprecated protocols it fails to disable). YAML line numbers come from PyYAML
compose marks. Static analysis only: a setting may be overridden at runtime.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

import yaml

from cryptoshift.inventory.algorithm_ids import Detection, classify_identifier
from cryptoshift.inventory.tls_config import analyse_cipher_string, analyse_groups, analyse_protocols

VERSION = "structured_config/1.0"

KEYWORDS = {"cipher", "ciphers", "ciphersuites", "suites", "protocol", "protocols", "group", "groups", "curve", "curves",
            "namedgroups", "alg", "algo", "algorithm", "algorithms", "kex", "exchange", "digest", "hash", "padding",
            "scheme", "wrap", "wrapping", "signing", "signature", "sigalgs", "keyalg", "keyalgorithm"}
DISABLE_TOKENS = {"disabled", "disable", "exclude", "excluded", "excludes", "deny", "denied", "blacklist", "blocked",
                  "forbidden", "prohibited", "unsupported", "disabledalgorithms", "legacyalgorithms", "removed"}
STRUCTURED_SUFFIXES = (".yaml", ".yml", ".properties", ".json")
SKIP_JSON = {"package.json", "package-lock.json", "composer.json", "tsconfig.json", "jsconfig.json"}
REQUIRED_DISABLED = ("SSLv3", "TLSv1", "TLSv1.1")


def _tokens(key: str) -> List[str]:
    return [t for t in re.split(r"[^a-z0-9]+", re.sub(r"([a-z])([A-Z])", r"\1_\2", key).lower()) if t]


def key_is_crypto(path: List[str]) -> bool:
    last = _tokens(path[-1]) if path else []
    joined = "".join(last)
    return bool(set(last) & KEYWORDS) or joined in KEYWORDS or ({"key", "type"} <= set(last)) or (
        "version" in last and any(t in ("ssl", "tls") for p in path for t in _tokens(p)))


def key_disables(path: List[str]) -> bool:
    toks = {t for p in path for t in _tokens(p)} | {"".join(_tokens(p)) for p in path}
    return bool(toks & DISABLE_TOKENS)


def analyse_value(value: str, path: List[str]) -> List[Detection]:
    """Classify the value of one crypto-keyword key."""
    v = str(value).strip().strip("'\"")
    if not v or len(v) > 2000:
        return []
    toks = set(_tokens(path[-1])) if path else set()
    if toks & {"cipher", "ciphers", "suites", "ciphersuites"} or v.upper().startswith("TLS_") or ":" in v and "-" in v:
        out = analyse_cipher_string(v)
        if out:
            return out
    if toks & {"protocols"} or ("enabled" in toks and "protocol" in toks):
        return analyse_protocols(v.replace(",", " "), apache_syntax=False)
    if toks & {"protocol", "version"}:
        return [d for item in re.split(r"[,\s]+", v) for d in classify_identifier(item) if d[0] == "TLS-protocol"]
    if toks & {"group", "groups", "curve", "curves", "namedgroups"}:
        out = analyse_groups(v)
        if out:
            return out
    found: List[Detection] = []
    for item in re.split(r"[,\s]+", v):
        found += classify_identifier(item, context="_".join(path[-1:]))
    return found


def _disabled_algorithms_gaps(value: str) -> List[Detection]:
    items = {i.strip().split(" ")[0].lower() for i in value.split(",")}
    missing = [p for p in REQUIRED_DISABLED if p.lower() not in items]
    if not missing:
        return []
    return [("TLS-protocol", "transport_protocol", "none", "medium",
             f"jdk.tls.disabledAlgorithms does not disable {', '.join(missing)} (JDK defaults may still apply)")]


# --- YAML ---------------------------------------------------------------------------------------------------------
def _walk_yaml(node: Any, path: List[str]) -> Iterator[Tuple[List[str], str, int]]:
    if isinstance(node, yaml.MappingNode):
        for k, v in node.value:
            if isinstance(k, yaml.ScalarNode):
                yield from _walk_yaml(v, path + [str(k.value)])
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            yield from _walk_yaml(item, path)
    elif isinstance(node, yaml.ScalarNode) and path:
        yield path, str(node.value), node.start_mark.line + 1


def scan_yaml_text(text: str) -> Iterator[Tuple[List[str], str, int]]:
    for doc in yaml.compose_all(text):
        if doc is not None:
            yield from _walk_yaml(doc, [])


# --- .properties / java.security -----------------------------------------------------------------------------------
def scan_properties_text(text: str) -> Iterator[Tuple[List[str], str, int]]:
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        start, line = i + 1, lines[i]
        while line.rstrip().endswith("\\") and i + 1 < len(lines):
            i += 1
            line = line.rstrip()[:-1] + " " + lines[i].strip()
        i += 1
        s = line.strip()
        if not s or s[0] in "#!":
            continue
        m = re.match(r"^([^=:\s]+)\s*[=:\s]\s*(.*)$", s)
        if m:
            yield m.group(1).split("."), m.group(2), start


# --- JSON ---------------------------------------------------------------------------------------------------------
_JSON_PAIR = re.compile(r'"([^"\\]{1,120})"\s*:\s*"([^"\\]{0,2000})"')
_JSON_ARRAY_START = re.compile(r'"([^"\\]{1,120})"\s*:\s*\[')
_JSON_STR = re.compile(r'"([^"\\]{0,200})"')


def scan_json_text(text: str) -> Iterator[Tuple[List[str], str, int]]:
    json.loads(text)  # raises ValueError on invalid JSON (reported as a parse error)
    array_key = None
    for n, line in enumerate(text.splitlines(), start=1):
        for m in _JSON_PAIR.finditer(line):
            yield [m.group(1)], m.group(2), n
        m = _JSON_ARRAY_START.search(line)
        if m:
            array_key = m.group(1)
            rest = line[m.end():]
            for s in _JSON_STR.findall(rest.split("]")[0]):
                yield [array_key], s, n
            if "]" in rest:
                array_key = None
            continue
        if array_key:
            if not _JSON_PAIR.search(line):
                for s in _JSON_STR.findall(line.split("]")[0]):
                    yield [array_key], s, n
            if "]" in line:
                array_key = None


def _is_protocol_list(path: List[str]) -> bool:
    toks = set(_tokens(path[-1])) if path else set()
    return "protocols" in toks or {"enabled", "protocol"} <= toks


def _combine_protocol_lists(pairs: Iterator[Tuple[List[str], str, int]]) -> List[Tuple[List[str], str, int]]:
    """List items of one protocol-list key (YAML sequence / JSON array) are judged together: [TLSv1.2, TLSv1.3]
    must not be read as "TLSv1.2 without TLS 1.3". The combined value keeps the first item's line."""
    out: List[Tuple[List[str], str, int]] = []
    for keypath, value, line in pairs:
        if out and _is_protocol_list(keypath) and out[-1][0] == keypath:
            out[-1] = (keypath, f"{out[-1][1]} {value}", out[-1][2])
        else:
            out.append((keypath, value, line))
    return out


def is_structured_config(path: Path) -> bool:
    name = path.name.lower()
    if name == "java.security":
        return True
    if name in SKIP_JSON or name.endswith(".lock.json"):
        return False
    return path.suffix.lower() in STRUCTURED_SUFFIXES


def scan_structured_text(text: str, path: Path) -> List[Dict[str, Any]]:
    """Raw detection dicts. Raises yaml.YAMLError / ValueError for unparsable files."""
    suffix, name = path.suffix.lower(), path.name.lower()
    if suffix in (".yaml", ".yml"):
        pairs, kind = scan_yaml_text(text), "yaml"
    elif suffix == ".json":
        pairs, kind = scan_json_text(text), "json"
    else:
        pairs, kind = scan_properties_text(text), "java.security" if name == "java.security" else "properties"
    lines = text.splitlines()
    hits: List[Dict[str, Any]] = []
    seen = set()
    for keypath, value, line in _combine_protocol_lists(pairs):
        dotted = ".".join(keypath)
        if dotted.lower() == "jdk.tls.disabledalgorithms":
            detections = _disabled_algorithms_gaps(value)
        elif key_disables(keypath) or not key_is_crypto(keypath):
            continue
        else:
            detections = analyse_value(value, keypath)
        for fam, purpose, ambiguity, conf, reason in detections:
            if (line, fam, purpose) in seen:
                continue
            seen.add((line, fam, purpose))
            hits.append({
                "line": line, "family": fam, "purpose": purpose, "ambiguity": ambiguity, "confidence": conf,
                "detected_value": f"{dotted} = {value}"[:200], "reason": f"{dotted}: {reason}",
                "library_or_protocol": kind, "snippet": lines[line - 1] if 0 < line <= len(lines) else "",
                "location": f"key {dotted} (line {line})",
            })
    return hits
