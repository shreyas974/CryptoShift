"""Relationship evidence between services, for Member 3's dependency graph. OBSERVED edges only; nothing is invented.

Sources (each edge carries file, line, kind, confidence and a redacted evidence snippet):
- nginx        `proxy_pass` / `grpc_pass` (directly or through an `upstream` block's `server` entries)
- haproxy      `server <name> <host>:<port>` lines inside a backend / listen section
- compose      `depends_on` and `links` of docker-compose services
- config       URLs (`scheme://host`) and host-like values of keys ending in host / url / endpoint / address in
               YAML, .properties, JSON and .conf files, plus explicit `depends_on` lists in service config files
- python       imports of another service's top-level package
A reference whose target cannot be matched to a known service is listed under `unknown_references` (never an edge).
Host matching: exact service id (high) or first DNS label / host name equal to a service id after normalising - and _
(medium). Loopback hosts and self references are ignored.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

import yaml

from cryptoshift.inventory.common import redact_snippet
from cryptoshift.inventory.services import COMPOSE_NAMES, ServiceCatalog, discover_services, norm_service, parse_compose, yaml_mapping_items

VERSION = "relationships/1.0"

LOOPBACK = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]", "host.docker.internal"}
URL_RE = re.compile(r"\b(?:https?|grpcs?|wss?|amqps?|postgres(?:ql)?|mysql|redis|rediss|mongodb|nats|kafka|tcp)://([A-Za-z0-9_.\-]+)(?::\d+)?")
HOST_KEY_RE = re.compile(r"(host|hostname|url|uri|endpoint|address|addr|upstream|server|base[-_]?url)$", re.I)
DEPENDS_KEYS = {"depends_on", "dependson", "dependencies_services", "upstream_services"}
NGINX_PASS_RE = re.compile(r"^\s*(proxy_pass|grpc_pass|uwsgi_pass|fastcgi_pass)\s+([^;]+);")
NGINX_UPSTREAM_RE = re.compile(r"^\s*upstream\s+([A-Za-z0-9_.\-]+)\s*\{")
NGINX_SERVER_RE = re.compile(r"^\s*server\s+([^;\s]+)")
TEXT_SUFFIXES = {".yaml", ".yml", ".properties", ".json", ".conf", ".cfg", ".ini", ".toml", ".py"}
SKIP_DIRS = {".git", ".venv", "venv", "env", "node_modules", "__pycache__"}


class _Collector:
    def __init__(self, cat: ServiceCatalog) -> None:
        self.cat = cat
        self.known = {norm_service(s): s for s in cat.known}
        self.edges: List[Dict[str, Any]] = []
        self.unknown: List[Dict[str, Any]] = []
        self._seen = set()

    def match_host(self, host: str) -> Tuple[Optional[str], str]:
        h = host.strip().strip("[]").lower()
        if norm_service(h) in self.known:
            return self.known[norm_service(h)], "high"
        first = norm_service(h.split(".", 1)[0])
        if first in self.known:
            return self.known[first], "medium"
        return None, "none"

    def add(self, source: str, target_ref: str, kind: str, rel: str, line: int, snippet: str, direct: Optional[str] = None,
            conf: Optional[str] = None) -> None:
        if target_ref.strip().lower() in LOOPBACK:
            return
        target, how = (direct, conf or "high") if direct else self.match_host(target_ref)
        if target is not None and target == source:
            return
        key = (source, target or target_ref, kind, rel, line)
        if key in self._seen:
            return
        self._seen.add(key)
        if target is None or source == "unknown":
            self.unknown.append({"source": source, "reference": target_ref, "kind": kind, "file": rel, "line": line,
                                 "reason": "source service unknown" if source == "unknown" and target else
                                 "reference does not match any known service"})
            return
        self.edges.append({"edge_id": f"REL-{len(self.edges) + 1:04d}", "source": source, "target": target, "kind": kind,
                           "provenance": "OBSERVED", "file": rel, "line": line, "confidence": how,
                           "evidence": redact_snippet(snippet), "reference": target_ref})


def _nginx(c: _Collector, rel: str, text: str, src: str) -> None:
    lines = text.splitlines()
    upstreams: Dict[str, List[Tuple[str, int]]] = {}
    current = None
    for n, raw in enumerate(lines, 1):
        line = raw.split("#", 1)[0]
        m = NGINX_UPSTREAM_RE.match(line)
        if m:
            current = m.group(1)
            upstreams[current] = []
            continue
        if current:
            ms = NGINX_SERVER_RE.match(line)
            if ms:
                upstreams[current].append((ms.group(1).split(":")[0], n))
            if "}" in line:
                current = None
    for n, raw in enumerate(lines, 1):
        m = NGINX_PASS_RE.match(raw.split("#", 1)[0])
        if not m:
            continue
        target = m.group(2).strip()
        um = re.match(r"^(?:[a-z]+://)?([A-Za-z0-9_.\-]+)", target)
        if not um:
            continue
        host = um.group(1)
        if host in upstreams:
            for srv, sline in upstreams[host]:
                c.add(src, srv, "nginx_upstream", rel, sline, lines[sline - 1])
        elif "$" not in target:
            c.add(src, host, f"nginx_{m.group(1)}", rel, n, raw)


def _haproxy(c: _Collector, rel: str, text: str, src: str) -> None:
    section = ""
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if re.match(r"^(backend|listen|frontend|global|defaults)\b", line):
            section = line.split()[0]
            continue
        if section in ("backend", "listen") and line.startswith("server "):
            parts = line.split()
            if len(parts) >= 3:
                c.add(src, parts[2].split(":")[0], "haproxy_server", rel, n, raw)


def _compose(c: _Collector, path: Path, rel: str) -> None:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for name, info in parse_compose(path, c.cat.root).items():
        for k, v in yaml_mapping_items(info["node"]):
            if k.value not in ("depends_on", "links"):
                continue
            items: List[Tuple[str, int]] = []
            if isinstance(v, yaml.SequenceNode):
                items = [(i.value.split(":")[0], i.start_mark.line + 1) for i in v.value if isinstance(i, yaml.ScalarNode)]
            elif isinstance(v, yaml.MappingNode):
                items = [(kk.value, kk.start_mark.line + 1) for kk, _ in v.value]
            for dep, line in items:
                tgt = c.known.get(norm_service(dep))
                c.add(name, dep, f"compose_{k.value}", rel, line, lines[line - 1], direct=tgt, conf="high")


def _walk_values(node: Any, path: List[str]):
    if isinstance(node, yaml.MappingNode):
        for k, v in node.value:
            if isinstance(k, yaml.ScalarNode):
                yield from _walk_values(v, path + [str(k.value)])
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            yield from _walk_values(item, path)
    elif isinstance(node, yaml.ScalarNode):
        yield path, str(node.value), node.start_mark.line + 1


def _config(c: _Collector, rel: str, text: str, src: str, suffix: str) -> None:
    lines = text.splitlines()
    pairs: List[Tuple[List[str], str, int]] = []
    if suffix in (".yaml", ".yml"):
        try:
            for doc in yaml.compose_all(text):
                if doc is not None:
                    pairs += list(_walk_values(doc, []))
        except yaml.YAMLError:
            return
    else:
        for n, raw in enumerate(lines, 1):
            s = raw.strip()
            if not s or s[0] in "#!;":
                continue
            m = re.match(r'^"?([A-Za-z0-9_.\-]+)"?\s*[=:]\s*"?([^"#]*)"?,?\s*$', s)
            if m:
                pairs.append(([m.group(1)], m.group(2).strip(), n))
    for path, value, n in pairs:
        key = path[-1] if path else ""
        if norm_service(key).replace(".", "_") in DEPENDS_KEYS or key.lower().endswith(("depends_on", "dependson")):
            for dep in re.split(r"[,\s\[\]]+", value):
                if dep.strip("'\""):
                    c.add(src, dep.strip("'\""), "config_depends_on", rel, n, lines[n - 1])
            continue
        for m in URL_RE.finditer(value):
            c.add(src, m.group(1), "config_url", rel, n, lines[n - 1])
        if not URL_RE.search(value) and HOST_KEY_RE.search(key.replace("-", "_")) and re.fullmatch(r"[A-Za-z0-9_.\-]+(:\d+)?", value or ""):
            if not value.replace(".", "").isdigit():
                c.add(src, value.split(":")[0], "config_host", rel, n, lines[n - 1])


def _python(c: _Collector, rel: str, text: str, src: str, packages: Dict[str, str]) -> None:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return
    lines = text.splitlines()
    for node in ast.walk(tree):
        mods: List[str] = []
        if isinstance(node, ast.Import):
            mods = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            mods = [node.module]
        for mod in mods:
            top = mod.split(".")[0]
            if top in packages and packages[top] != src:
                c.add(src, top, "python_import", rel, node.lineno, lines[node.lineno - 1], direct=packages[top], conf="high")
        # Module-level DEPENDS_ON = [...] lists in service files
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id.upper() in ("DEPENDS_ON", "DEPENDENCIES") for t in node.targets):
            if isinstance(node.value, (ast.List, ast.Tuple)):
                for e in node.value.elts:
                    if isinstance(e, ast.Constant) and isinstance(e.value, str):
                        c.add(src, e.value, "config_depends_on", rel, node.lineno, lines[node.lineno - 1])


def _service_packages(cat: ServiceCatalog, files: List[Path]) -> Dict[str, str]:
    """top-level importable package name -> owning service (a folder with __init__.py inside a service)."""
    out: Dict[str, str] = {}
    for p in files:
        if p.name != "__init__.py":
            continue
        rel = p.relative_to(cat.root).as_posix()
        pkg = PurePosixPath(rel).parent
        att = cat.attribute(rel)
        if att.service_id != "unknown" and (pkg.parent.as_posix() in cat.folder_services or pkg.parent.as_posix() in ("", ".")
                                            or any(pkg.parent.as_posix() == d for i in cat.compose_services.values() for d, _ in i["dirs"])):
            out.setdefault(pkg.name, att.service_id)
    return out


def extract_relationships(target: Path, catalog: Optional[ServiceCatalog] = None,
                          extra_known: Optional[List[str]] = None) -> Dict[str, Any]:
    from cryptoshift.inventory.scan import is_sensitive_name

    target = Path(target)
    cat = catalog or discover_services(target, extra_known=extra_known)
    root = cat.root
    files = [target] if target.is_file() else [
        p for p in sorted(target.rglob("*"))
        if p.is_file() and not any(part in SKIP_DIRS for part in p.relative_to(target).parts[:-1])]
    files = [p for p in files if not is_sensitive_name(p.name)]
    c = _Collector(cat)
    packages = _service_packages(cat, files)
    for p in files:
        rel = p.relative_to(root).as_posix()
        if p.name in COMPOSE_NAMES:
            _compose(c, p, rel)
            continue
        suffix = p.suffix.lower()
        if suffix not in TEXT_SUFFIXES or p.stat().st_size > 2_000_000:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        src = cat.attribute(rel).service_id
        if suffix == ".py":
            _python(c, rel, text, src, packages)
            continue
        if suffix in (".conf",) and re.search(r"^\s*(proxy_pass|grpc_pass|upstream)\b", text, re.M):
            _nginx(c, rel, text, src)
            continue
        if suffix == ".cfg" and re.search(r"^\s*(backend|listen)\b", text, re.M):
            _haproxy(c, rel, text, src)
            continue
        _config(c, rel, text, src, suffix)
    return {"format": "cryptoshift-relationships/1.0", "provenance_policy": "OBSERVED only; unresolved references listed, never turned into edges",
            "known_services": cat.known, "edges": c.edges, "unknown_references": c.unknown,
            "summary": {"edges": len(c.edges), "unknown_references": len(c.unknown),
                        "by_kind": {k: sum(1 for e in c.edges if e["kind"] == k) for k in sorted({e["kind"] for e in c.edges})}}}
