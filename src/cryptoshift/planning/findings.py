"""Collect scanner findings for planning (Member 3).

Merges the legacy file scanner (`scanner.scan_repository_path`: YAML/Python constants/nginx) with the Stage 1
inventory detectors (`inventory.scan_inventory`). Duplicates on the same (file, line, family group) keep the
inventory finding. All file paths are made relative to the repository root (never absolute local paths).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from cryptoshift.inventory import scan_inventory
from cryptoshift.models import CryptoFinding
from cryptoshift.optimization.auth_check import PROJECT_ROOT
from cryptoshift.scanner import scan_repository_path

CONFIG_PATH = Path(__file__).with_name("planning_config.json")

FAMILY_GROUP = {
    "RSA": "RSA", "RSA-2048": "RSA", "EC": "EC", "ECDSA": "EC", "ECDSA-P256": "EC", "ECDH": "EC",
    "ECDHE-P256": "EC", "X25519": "EC", "X448": "EC", "Ed25519": "EC", "Ed448": "EC", "EdDSA": "EC",
    "ECDSA/DSA": "EC", "DSA": "DSA", "DH": "DH", "DH-2048": "DH", "3DES": "LEGACY_SYM", "DES": "LEGACY_SYM",
    "RC4": "LEGACY_SYM", "Blowfish": "LEGACY_SYM", "SHA-1": "WEAK_HASH", "MD5": "WEAK_HASH",
    "TLS-protocol": "TLS_PROTOCOL", "TLS-cipher-policy": "CIPHER_POLICY", "X.509-unknown-key": "CERT_UNKNOWN",
}


def load_config() -> Dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def family_group(f: CryptoFinding) -> str:
    if f.detector == "dependency_manifest":
        return "DEPENDENCY"
    return FAMILY_GROUP.get(f.algorithm_family or f.legacy_algorithm, f.algorithm_family or f.legacy_algorithm)


def rel_to_root(path_str: str, root: Path = PROJECT_ROOT) -> str:
    p = Path(path_str)
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return p.name


def collect_findings(target: Path) -> Tuple[List[CryptoFinding], Dict[str, Dict[str, Any]]]:
    """Return merged findings (service-attributed, repo-relative paths) and per-service file metadata."""
    target = Path(target)
    legacy, meta = scan_repository_path(target)
    file_to_service: Dict[str, str] = {}
    for svc, m in meta.items():
        for fp in m.get("files", []):
            file_to_service[rel_to_root(fp)] = svc

    merged: Dict[Tuple[str, int, str], CryptoFinding] = {}
    base = target.parent if target.is_file() else target
    inv, _ = scan_inventory(target)
    for f in inv:
        f.file_path = rel_to_root(str(base / f.file_path))
        f.service_id = file_to_service.get(f.file_path, f.service_id)
        merged[(f.file_path, f.line_number, family_group(f))] = f
    for f in legacy:
        f.file_path = rel_to_root(f.file_path)
        f.detector = f.detector or "legacy"
        f.algorithm_family = f.algorithm_family or f.legacy_algorithm
        merged.setdefault((f.file_path, f.line_number, family_group(f)), f)

    findings = sorted(merged.values(), key=lambda f: (f.service_id, f.file_path, f.line_number, f.finding_id))
    services = {
        svc: {"service_id": svc, "owner": m.get("owner", "unknown"),
              "files": sorted(rel_to_root(fp) for fp in m.get("files", [])),
              "_abs": {rel_to_root(fp): Path(fp) for fp in m.get("files", [])}}  # internal; never serialised
        for svc, m in meta.items()
    }
    return findings, services
