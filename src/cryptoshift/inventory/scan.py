"""Stage 1 inventory scan: walk a directory, dispatch each file to a detector, emit CryptoFinding records."""

from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from cryptoshift.inventory import haproxy, java_source, python_ast, relationships, services, shell_scripts, structured_config
from cryptoshift.inventory.certificates import CERT_SUFFIXES, inspect_certificate_file, scan_certificate_file
from cryptoshift.inventory.common import make_finding
from cryptoshift.inventory.manifests import manifest_kind, scan_manifest_text
from cryptoshift.inventory.python_ast import scan_python_source
from cryptoshift.inventory.tls_config import looks_like_tls_config, scan_tls_config_text
from cryptoshift.models import CryptoFinding

DETECTOR_VERSIONS = {
    "python_ast": python_ast.VERSION,
    "tls_config": "tls_config/1.1 (Apache ECDHParameters, DHE-DSS)",
    "dependency_manifest": "manifests/1.0",
    "certificate": "certificates/1.0",
    "structured_config": structured_config.VERSION,
    "haproxy": haproxy.VERSION,
    "shell_script": shell_scripts.VERSION,
    "java_source": java_source.VERSION,
    "service_attribution": services.VERSION,
    "relationships": relationships.VERSION,
}

SKIP_DIRS = {".git", ".venv", "venv", "env", "node_modules", "__pycache__", ".tox", ".mypy_cache", ".pytest_cache"}
SENSITIVE_SUFFIXES = (".key", ".p12", ".pfx", ".jks", ".keystore", ".kdbx")
CONFIG_SUFFIXES = (".conf", ".nginx", ".cnf", ".htaccess", ".inc")
MAX_TEXT_BYTES = 2_000_000


def is_sensitive_name(name: str) -> bool:
    """Files that are never opened: .env variants, qcloud.env, key stores, SSH private keys."""
    n = name.lower()
    return (
        n == ".env" or n.startswith(".env.") or n.endswith(".env")
        or n.endswith(SENSITIVE_SUFFIXES)
        or n.startswith(("id_rsa", "id_ecdsa", "id_ed25519", "id_dsa")) and not n.endswith(".pub")
    )


def _iter_files(target: Path) -> List[Path]:
    if target.is_file():
        return [target]
    out: List[Path] = []
    for p in sorted(target.rglob("*")):
        if any(part in SKIP_DIRS for part in p.relative_to(target).parts[:-1]):
            continue
        if p.is_file():
            out.append(p)
    return out


def _cert_inspector(path: Path) -> Optional[Dict[str, Any]]:
    if path.suffix.lower() not in CERT_SUFFIXES or is_sensitive_name(path.name):
        return None
    info = inspect_certificate_file(path)
    return None if not info or info.get("private_key_material") else info


def detect_file(path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """Return (detector_name, raw hits) for one file; detector '' means not applicable."""
    name, suffix = path.name, path.suffix.lower()
    if path.stat().st_size > MAX_TEXT_BYTES:
        return "", []
    if suffix in CERT_SUFFIXES:
        return "certificate", scan_certificate_file(path)
    if suffix == ".py":
        text = path.read_text(encoding="utf-8", errors="replace")
        return "python_ast", scan_python_source(text)
    if manifest_kind(name):
        text = path.read_text(encoding="utf-8", errors="replace")
        return "dependency_manifest", scan_manifest_text(text, name)
    if suffix == ".java":
        return "java_source", java_source.scan_java_source(path.read_text(encoding="utf-8", errors="replace"))
    if shell_scripts.is_shell_or_dockerfile(path):
        return "shell_script", shell_scripts.scan_shell_text(path.read_text(encoding="utf-8", errors="replace"), path)
    if structured_config.is_structured_config(path):
        text = path.read_text(encoding="utf-8", errors="replace")
        return "structured_config", structured_config.scan_structured_text(text, path)
    if suffix in CONFIG_SUFFIXES or suffix in ("", ".cfg"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if haproxy.looks_like_haproxy(text, path):
            return "haproxy", haproxy.scan_haproxy_text(text, path, cert_inspector=_cert_inspector)
        if suffix != ".cfg" and looks_like_tls_config(text, path):
            return "tls_config", scan_tls_config_text(text, path, cert_inspector=_cert_inspector)
    return "", []


EVIDENCE_TYPE = {
    "python_ast": "source_code",
    "tls_config": "config_file",
    "dependency_manifest": "dependency_manifest",
    "certificate": "certificate_file",
    "structured_config": "config_file",
    "haproxy": "config_file",
    "shell_script": "script",
    "java_source": "source_code",
}


def scan_inventory(target: Path, service_id: Optional[str] = None,
                   extra_known_services: Optional[List[str]] = None) -> Tuple[List[CryptoFinding], Dict[str, Any]]:
    """Scan `target` (file or directory). Paths in findings are relative to `target`.

    service_id: if given, every finding gets it (basis "caller-supplied"); otherwise each file is attributed with the
    documented rules in `inventory.services` and stays "unknown" when no rule matches.
    """
    target = Path(target)
    root = target.parent if target.is_file() else target
    catalog = services.discover_services(target, extra_known=extra_known_services)
    findings: List[CryptoFinding] = []
    stats: Dict[str, Any] = {"files_seen": 0, "files_by_detector": Counter(), "skipped_sensitive": 0, "parse_errors": [],
                             "input_sha256": {}, "service_catalog": catalog.to_dict(), "_catalog": catalog}

    for path in _iter_files(target):
        rel = path.relative_to(root).as_posix()
        stats["files_seen"] += 1
        if is_sensitive_name(path.name):
            stats["skipped_sensitive"] += 1
            continue
        try:
            detector, hits = detect_file(path)
        except SyntaxError as exc:
            stats["parse_errors"].append({"file": rel, "error": f"SyntaxError line {exc.lineno}"})
            continue
        except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
            stats["parse_errors"].append({"file": rel, "error": type(exc).__name__})
            continue
        if not detector:
            continue
        stats["files_by_detector"][detector] += 1
        stats["input_sha256"][rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        if service_id:
            att = services.Attribution(service_id, "caller-supplied service_id", "high", "explicit")
        else:
            att = catalog.attribute(rel)
        for h in hits:
            findings.append(
                make_finding(
                    index=len(findings) + 1,
                    rel_path=rel,
                    line=int(h["line"]),
                    family=h["family"],
                    purpose=h["purpose"],
                    detector=detector,
                    detected_value=h["detected_value"],
                    reason=h["reason"],
                    confidence=h["confidence"],
                    ambiguity=h["ambiguity"],
                    evidence_type=EVIDENCE_TYPE[detector],
                    library_or_protocol=h.get("library_or_protocol", "unknown"),
                    snippet=h.get("snippet", ""),
                    location=h.get("location"),
                    service_id=att.service_id,
                    algorithm_label=h.get("algorithm_label"),
                    service_id_basis=att.basis,
                    service_id_confidence=att.confidence,
                )
            )
    stats["files_by_detector"] = dict(stats["files_by_detector"])
    return findings, stats
