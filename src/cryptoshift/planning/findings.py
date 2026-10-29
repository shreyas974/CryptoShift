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
from cryptoshift.inventory.services import COMPOSE_NAMES
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


def collect_findings(target: Path, extra_known_services: List[str] | None = None) -> Tuple[List[CryptoFinding], Dict[str, Dict[str, Any]]]:
    """Return merged findings (service-attributed, repo-relative paths) and per-service file metadata.

    Service attribution: Member 2's documented rules (inventory/services.py) first; only where they give "unknown"
    is the legacy scanner's descriptor-file map used, and the basis says so."""
    target = Path(target)
    base = target.parent if target.is_file() else target
    legacy, meta = scan_repository_path(target)
    legacy_service = {rel_to_root(fp): svc for svc, m in meta.items() for fp in m.get("files", [])}
    inv, stats = scan_inventory(target, extra_known_services=extra_known_services)
    catalog = stats["_catalog"]

    abs_of: Dict[str, Path] = {}  # repo-relative path -> real path (internal; never serialised)
    attribution: Dict[str, Tuple[str, str, str]] = {}

    def attribute(real: Path) -> Tuple[str, str, str]:
        rel = rel_to_root(str(real))
        abs_of.setdefault(rel, real)
        if rel not in attribution:
            try:
                a = catalog.attribute(real.resolve().relative_to(base.resolve()).as_posix())
                attribution[rel] = (a.service_id, a.basis, a.confidence)
            except ValueError:
                attribution[rel] = ("unknown", "outside scan root", "none")
            # A compose file describes the whole system, never one service: no legacy fallback for it.
            if attribution[rel][0] == "unknown" and rel in legacy_service and real.name not in COMPOSE_NAMES:
                attribution[rel] = (legacy_service[rel], "legacy scanner file map (scanner.py); Member 2 rules gave unknown", "low")
        return attribution[rel]

    merged: Dict[Tuple[str, int, str], CryptoFinding] = {}
    for f in inv:
        real = base / f.file_path
        f.file_path = rel_to_root(str(real))
        f.service_id, f.service_id_basis, f.service_id_confidence = attribute(real)
        merged[(f.file_path, f.line_number, family_group(f))] = f
    for f in legacy:
        real = Path(f.file_path)
        f.file_path = rel_to_root(f.file_path)
        f.service_id, f.service_id_basis, f.service_id_confidence = attribute(real)
        f.detector = f.detector or "legacy"
        f.algorithm_family = f.algorithm_family or f.legacy_algorithm
        merged.setdefault((f.file_path, f.line_number, family_group(f)), f)
    for svc, m in meta.items():  # files the legacy scanner read without findings still belong to a service
        for fp in m.get("files", []):
            attribute(Path(fp))

    findings = sorted(merged.values(), key=lambda f: (f.service_id, f.file_path, f.line_number, f.finding_id))
    names = ({s for s, _, _ in attribution.values()} | set(catalog.known)) - {"unknown"}
    services = {
        svc: {"service_id": svc,
              "owner": next((m.get("owner", "unknown") for s, m in meta.items() if s == svc), "unknown"),
              "files": sorted(r for r, a in attribution.items() if a[0] == svc),
              "_abs": {r: abs_of[r] for r, a in attribution.items() if a[0] == svc}}  # internal; never serialised
        for svc in sorted(names)
    }
    return findings, services
