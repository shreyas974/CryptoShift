"""Service attribution: which service does a scanned file belong to? Documented rules, first match wins.

Rule order (basis strings are copied into every finding as `service_id_basis`):
  1. declared   - the file itself declares its service: a top-level `service_id:` (YAML/JSON), `SERVICE_ID = "..."`
                  (Python), `spring.application.name=` (properties), or a `Service ID: x` header comment in the first
                  10 lines. Confidence high (medium for the comment form).
  2. compose    - the file sits inside a docker-compose service's build context, or is mounted into it as a volume.
                  Confidence high.
  3. folder     - nearest ancestor folder holding a service marker (Dockerfile, pyproject.toml, setup.py, package.json,
                  pom.xml, build.gradle, go.mod), or a direct child of a `services/`, `apps/` or `microservices/`
                  folder. Confidence medium.
  4. file_name  - a config file whose name is not generic (e.g. `payments_tls.conf` -> `payments_tls`).
                  Confidence low.
  5. unknown    - nothing matched; service_id stays "unknown". Never guessed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

import yaml

VERSION = "services/1.0"

COMPOSE_NAMES = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")
SERVICE_MARKERS = ("Dockerfile", "pyproject.toml", "setup.py", "package.json", "pom.xml", "build.gradle",
                   "build.gradle.kts", "go.mod")
SERVICE_PARENT_DIRS = {"services", "apps", "microservices"}
GENERIC_STEMS = {"nginx", "default", "app", "application", "config", "settings", "haproxy", "openssl", "ssl", "tls",
                 "main", "server", "site", "index", "values", "docker-compose", "compose", "dockerfile", "java",
                 "httpd", "apache2", "options-ssl-nginx", "options-ssl-apache", "init", "__init__", "conftest"}
CONFIG_SUFFIXES = {".conf", ".cfg", ".yaml", ".yml", ".properties", ".json", ".ini", ".cnf", ".toml"}
SKIP_DIRS = {".git", ".venv", "venv", "env", "node_modules", "__pycache__", ".tox"}

_DECL_YAML = re.compile(r"^service_id\s*:\s*['\"]?([A-Za-z0-9_.-]+)['\"]?\s*(#.*)?$")
_DECL_PY = re.compile(r"^SERVICE_ID\s*(?::\s*str\s*)?=\s*['\"]([A-Za-z0-9_.-]+)['\"]")
_DECL_PROPS = re.compile(r"^spring\.application\.name\s*[=:]\s*([A-Za-z0-9_.-]+)\s*$")
_DECL_COMMENT = re.compile(r"^\s*(?:#|//|;|\*)\s*service[ _-]?id\s*:\s*([A-Za-z0-9_.-]+)\s*$", re.I)


def norm_service(name: str) -> str:
    return name.strip().lower().replace("-", "_")


@dataclass
class Attribution:
    service_id: str
    basis: str
    confidence: str  # high | medium | low | none
    rule: str

    def to_dict(self) -> Dict[str, str]:
        return {"service_id": self.service_id, "service_id_basis": self.basis,
                "service_id_confidence": self.confidence, "rule": self.rule}


@dataclass
class ServiceCatalog:
    root: Path
    compose_files: List[str] = field(default_factory=list)
    compose_services: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # name -> {dirs, file, line}
    folder_services: Dict[str, str] = field(default_factory=dict)  # rel dir -> service id
    declared: Dict[str, Tuple[str, int, str]] = field(default_factory=dict)  # rel file -> (service, line, form)
    extra_known: List[str] = field(default_factory=list)

    @property
    def known(self) -> List[str]:
        names = set(self.compose_services) | set(self.folder_services.values()) | {d[0] for d in self.declared.values()}
        return sorted(names | set(self.extra_known))

    def attribute(self, rel_path: str) -> Attribution:
        rel = PurePosixPath(rel_path)
        if rel_path in self.declared:
            svc, line, form = self.declared[rel_path]
            return Attribution(svc, f"declared in file ({form}, line {line})", "medium" if form == "header comment" else "high", "declared")
        best: Optional[Tuple[int, str, str]] = None
        for name, info in self.compose_services.items():
            for d, how in info["dirs"]:
                dp = PurePosixPath(d)
                if d in ("", ".") or rel == dp or dp in rel.parents:
                    depth = len(dp.parts) if d not in ("", ".") else 0
                    if best is None or depth > best[0]:
                        best = (depth, name, f"docker-compose service '{name}' {how} '{d or '.'}' ({info['file']}:{info['line']})")
        if best and best[0] > 0:
            return Attribution(best[1], best[2], "high", "compose")
        for parent in rel.parents:
            key = parent.as_posix()
            if key in self.folder_services and key not in ("", "."):
                return Attribution(self.folder_services[key], f"nearest service folder '{key}'", "medium", "folder")
        if rel.suffix.lower() in CONFIG_SUFFIXES and rel.stem.lower() not in GENERIC_STEMS and rel.name not in COMPOSE_NAMES:
            return Attribution(norm_service(rel.stem), f"config file name '{rel.name}'", "low", "file_name")
        if best:  # compose context '.' (whole repo) is too broad to be more than low confidence
            return Attribution(best[1], best[2], "low", "compose")
        return Attribution("unknown", "no attribution rule matched", "none", "unknown")

    def to_dict(self) -> Dict[str, Any]:
        return {"compose_files": self.compose_files,
                "compose_services": {k: {"dirs": [d for d, _ in v["dirs"]], "file": v["file"], "line": v["line"]}
                                     for k, v in sorted(self.compose_services.items())},
                "folder_services": dict(sorted(self.folder_services.items())),
                "declared_in_files": {k: {"service_id": v[0], "line": v[1], "form": v[2]} for k, v in sorted(self.declared.items())},
                "known_services": self.known}


def _rel(p: Path, root: Path) -> str:
    return p.relative_to(root).as_posix()


def _iter(root: Path) -> List[Path]:
    if root.is_file():
        return [root]
    return [p for p in sorted(root.rglob("*"))
            if p.is_file() and not any(part in SKIP_DIRS for part in p.relative_to(root).parts[:-1])]


def yaml_mapping_items(node: Any) -> List[Tuple[Any, Any]]:
    return node.value if isinstance(node, yaml.MappingNode) else []


def parse_compose(path: Path, root: Path) -> Dict[str, Dict[str, Any]]:
    """service name -> {dirs: [(rel dir, how)], file, line, node}. Uses yaml.compose for line numbers."""
    try:
        doc = yaml.compose(path.read_text(encoding="utf-8", errors="replace"))
    except yaml.YAMLError:
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    base = path.parent
    services = next((v for k, v in yaml_mapping_items(doc) if getattr(k, "value", None) == "services"), None)
    for k, v in yaml_mapping_items(services):
        name = norm_service(k.value)
        dirs: List[Tuple[str, str]] = []
        for kk, vv in yaml_mapping_items(v):
            if kk.value == "build":
                ctx = vv.value if isinstance(vv, yaml.ScalarNode) else next(
                    (c.value for ck, c in yaml_mapping_items(vv) if ck.value == "context"), None)
                if isinstance(ctx, str):
                    dirs.append((_norm_dir(base / ctx, root), "build context"))
            if kk.value == "volumes" and isinstance(vv, yaml.SequenceNode):
                for item in vv.value:
                    if isinstance(item, yaml.ScalarNode) and item.value.startswith((".", "/")) and ":" in item.value:
                        host = item.value.split(":", 1)[0]
                        if host.startswith("."):
                            dirs.append((_norm_dir(base / host, root), "volume mount"))
        out[name] = {"dirs": [d for d in dirs if d[0] is not None], "file": _rel(path, root), "line": k.start_mark.line + 1, "node": v}
    return out


def _norm_dir(p: Path, root: Path) -> Optional[str]:
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def _declared(path: Path, rel: str) -> Optional[Tuple[str, int, str]]:
    suffix = path.suffix.lower()
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for n, line in enumerate(lines[:200], start=1):
        if suffix in (".yaml", ".yml") and (m := _DECL_YAML.match(line)):
            return norm_service(m.group(1)), n, "service_id key"
        if suffix == ".py" and (m := _DECL_PY.match(line)):
            return norm_service(m.group(1)), n, "SERVICE_ID constant"
        if suffix == ".properties" and (m := _DECL_PROPS.match(line.strip())):
            return norm_service(m.group(1)), n, "spring.application.name"
    if suffix == ".json":
        try:
            data = json.loads("\n".join(lines))
        except ValueError:
            data = None
        if isinstance(data, dict) and isinstance(data.get("service_id"), str):
            n = next((i for i, l in enumerate(lines, 1) if '"service_id"' in l), 1)
            return norm_service(data["service_id"]), n, "service_id key"
    for n, line in enumerate(lines[:10], start=1):
        if m := _DECL_COMMENT.match(line):
            return norm_service(m.group(1)), n, "header comment"
    return None


def discover_services(target: Path, extra_known: Optional[List[str]] = None) -> ServiceCatalog:
    target = Path(target)
    root = target.parent if target.is_file() else target
    from cryptoshift.inventory.scan import is_sensitive_name  # local import: scan imports this module

    cat = ServiceCatalog(root=root, extra_known=[norm_service(s) for s in (extra_known or [])])
    files = [p for p in _iter(target) if not is_sensitive_name(p.name)]
    for p in files:
        rel = _rel(p, root)
        if p.name in COMPOSE_NAMES:
            cat.compose_files.append(rel)
            for name, info in parse_compose(p, root).items():
                cat.compose_services.setdefault(name, info)
        if p.name in SERVICE_MARKERS:
            d = PurePosixPath(rel).parent.as_posix()
            if d not in ("", "."):
                cat.folder_services.setdefault(d, norm_service(PurePosixPath(d).name))
        parts = PurePosixPath(rel).parts
        for i, part in enumerate(parts[:-2]):
            if part.lower() in SERVICE_PARENT_DIRS:
                d = PurePosixPath(*parts[: i + 2]).as_posix()
                cat.folder_services.setdefault(d, norm_service(parts[i + 1]))
        if p.suffix.lower() in (".yaml", ".yml", ".py", ".properties", ".json", ".conf", ".cfg") and p.name not in COMPOSE_NAMES:
            decl = _declared(p, rel)
            if decl:
                cat.declared[rel] = decl
    return cat
