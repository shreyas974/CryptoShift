"""Service dependency graph with provenance on every edge (Member 3).

Edge direction: (upstream, downstream) = (provider, consumer). Scheduling rule: upstream migrates no later than
downstream. Provenance:
- OBSERVED: evidence in code/config with file and line (nginx proxy_pass/upstream/grpc_pass URLs, Python
  `DEPENDS_ON`, YAML `depends_on`, https:// endpoint URLs in YAML values).
- DECLARED: the synthetic service descriptor `demo_bank_app/services.py`.
- INFERRED: a known service id mentioned in a configuration string value that is not a dependency key; the
  direction (mentioning service consumes mentioned service) is an assumption recorded in `reason`.
Unknown endpoints, observed/declared conflicts and cycles are reported, never dropped.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

import networkx as nx

from cryptoshift.planning.findings import rel_to_root

URL_RE = re.compile(r"(?:https?|grpcs?)://([A-Za-z0-9_\-]+)(?:[.:/]|$)")
NGINX_DEP_RE = re.compile(r"^\s*(proxy_pass|grpc_pass|uwsgi_pass|server)\s+([^;#]+);")
NGINX_SVC_RE = re.compile(r"#\s*Service ID:\s*([A-Za-z0-9_\-]+)", re.I)


def _edge(up: str, down: str, prov: str, file: Optional[str] = None, line: Optional[int] = None,
          reason: str = "", evidence: str = "") -> Dict[str, Any]:
    return {"upstream": up, "downstream": down, "provenance": prov, "file": file, "line": line,
            "reason": reason, "evidence": evidence}


def _host_to_service(host: str, known: Set[str]) -> Optional[str]:
    h = host.split(".")[0].replace("-", "_")
    return h if h in known else None


def observed_edges(files: Iterable[Path], file_service: Dict[str, str], known: Set[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Scan config/source files for dependency evidence. Returns {'edges': [...], 'unknown_endpoints': [...]}."""
    edges: List[Dict[str, Any]] = []
    unknown: List[Dict[str, Any]] = []
    for path in files:
        rel = rel_to_root(str(path))
        text = path.read_text(encoding="utf-8", errors="replace")
        svc = file_service.get(rel)
        suffix = path.suffix.lower()
        if suffix in (".conf", ".nginx"):
            for n, raw in enumerate(text.splitlines(), start=1):
                m = NGINX_SVC_RE.search(raw)
                if m and not svc:
                    svc = m.group(1)
                d = NGINX_DEP_RE.match(raw)
                if not d or not svc:
                    continue
                for host in URL_RE.findall(d.group(2)) or ([d.group(2).split(":")[0].strip()] if d.group(1) == "server" else []):
                    target = _host_to_service(host, known)
                    if target and target != svc:
                        edges.append(_edge(target, svc, "OBSERVED", rel, n, f"nginx {d.group(1)} to {host}", raw.strip()))
                    elif not target:
                        unknown.append({"service": svc, "endpoint": host, "file": rel, "line": n})
        elif suffix == ".py" and svc:
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in tree.body:
                if (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DEPENDS_ON" for t in node.targets)
                        and isinstance(node.value, (ast.List, ast.Tuple))):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            dep = elt.value
                            if dep in known:
                                edges.append(_edge(dep, svc, "OBSERVED", rel, elt.lineno, "Python DEPENDS_ON", dep))
                            else:
                                unknown.append({"service": svc, "endpoint": dep, "file": rel, "line": elt.lineno})
        elif suffix in (".yaml", ".yml") and svc:
            import yaml

            try:
                root = yaml.compose(text)
            except yaml.YAMLError:
                continue
            edges += _yaml_edges(root, svc, rel, known, unknown)
    return {"edges": edges, "unknown_endpoints": unknown}


def _yaml_edges(root: Any, svc: str, rel: str, known: Set[str], unknown: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    import yaml

    out: List[Dict[str, Any]] = []

    def walk(node: Any, key: str = "") -> None:
        if isinstance(node, yaml.MappingNode):
            for k, v in node.value:
                walk(v, str(k.value))
        elif isinstance(node, yaml.SequenceNode):
            for item in node.value:
                if key == "depends_on" and isinstance(item, yaml.ScalarNode):
                    dep, line = str(item.value), item.start_mark.line + 1
                    if dep in known:
                        out.append(_edge(dep, svc, "OBSERVED", rel, line, "YAML depends_on", dep))
                    else:
                        unknown.append({"service": svc, "endpoint": dep, "file": rel, "line": line})
                else:
                    walk(item, key)
        elif isinstance(node, yaml.ScalarNode) and key not in ("service_id", "service_name"):
            val, line = str(node.value), node.start_mark.line + 1
            for host in URL_RE.findall(val):
                target = _host_to_service(host, known)
                if target and target != svc:
                    out.append(_edge(target, svc, "OBSERVED", rel, line, f"endpoint URL in '{key}'", val))
                elif not target:
                    unknown.append({"service": svc, "endpoint": host, "file": rel, "line": line})
            if not URL_RE.search(val):
                for other in known:
                    if other != svc and re.search(rf"\b{re.escape(other)}\b", val):
                        out.append(_edge(other, svc, "INFERRED", rel, line,
                                         f"service id '{other}' mentioned in value of '{key}'; direction assumed "
                                         f"({svc} consumes {other})", val))

    if root is not None:
        walk(root)
    return out


def member2_observed_edges(target: Path, known: Set[str]) -> Dict[str, List[Dict[str, Any]]]:
    """OBSERVED edges from Member 2's relationship evidence (inventory/relationships.py).

    Member 2 edges are (source = consumer, target = provider); here they become (upstream = provider,
    downstream = consumer). Unresolved references stay visible as unknown endpoints, never as edges."""
    from cryptoshift.inventory.relationships import extract_relationships

    target = Path(target)
    base = target.parent if target.is_file() else target
    rel = extract_relationships(target, extra_known=sorted(known))
    edges = [
        dict(_edge(e["target"], e["source"], "OBSERVED", rel_to_root(str(base / e["file"])), e["line"],
                   f"{e['kind']} ({e['confidence']} confidence host match)" if e["kind"] in ("nginx_proxy_pass", "config_url", "config_host")
                   else e["kind"], e["evidence"]),
             kind=e["kind"], confidence=e["confidence"], evidence_id=e["edge_id"], producer="inventory.relationships (Member 2)")
        for e in rel["edges"] if e["source"] in known and e["target"] in known
    ]
    unknown = [{"service": u["source"], "endpoint": u["reference"], "file": rel_to_root(str(base / u["file"])),
                "line": u["line"], "kind": u["kind"], "reason": u["reason"]} for u in rel["unknown_references"]]
    return {"edges": edges, "unknown_endpoints": unknown}


def declared_edges(descriptor: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        _edge(dep, sid, "DECLARED", "demo_bank_app/services.py", None, "synthetic service descriptor")
        for sid, meta in descriptor.items() for dep in meta.get("dependencies", [])
    ]


def build_graph(services: Iterable[str], edges: List[Dict[str, Any]]) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    g.add_nodes_from(services)
    for e in edges:
        g.add_edge(e["upstream"], e["downstream"], **{k: v for k, v in e.items() if k not in ("upstream", "downstream")})
    return g


def constraint_digraph(g: nx.MultiDiGraph, enforced: Iterable[str]) -> nx.DiGraph:
    enforced = set(enforced)
    d = nx.DiGraph()
    d.add_nodes_from(g.nodes)
    for u, v, data in g.edges(data=True):
        if data["provenance"] in enforced:
            d.add_edge(u, v)
    return d


def analyse_graph(g: nx.MultiDiGraph, enforced: Iterable[str]) -> Dict[str, Any]:
    """Cycles (on enforced edges), observed-vs-declared conflicts, and per-pair provenance."""
    d = constraint_digraph(g, enforced)
    pairs: Dict[tuple, Set[str]] = {}
    for u, v, data in g.edges(data=True):
        pairs.setdefault((u, v), set()).add(data["provenance"])
    conflicts = []
    for (u, v), provs in sorted(pairs.items()):
        if "OBSERVED" in provs and "DECLARED" not in provs:
            conflicts.append({"upstream": u, "downstream": v, "issue": "OBSERVED in code/config but not DECLARED in descriptor"})
        if "DECLARED" in provs and "OBSERVED" not in provs:
            conflicts.append({"upstream": u, "downstream": v, "issue": "DECLARED in descriptor but no OBSERVED evidence in scanned files"})
    cycles = [list(c) for c in nx.simple_cycles(d)]
    return {
        "enforced_provenance": sorted(set(enforced)),
        "cycles": cycles,
        "has_cycles": bool(cycles),
        "conflicts": conflicts,
        "edge_counts": {p: sum(1 for *_, data in g.edges(data=True) if data["provenance"] == p)
                        for p in ("OBSERVED", "DECLARED", "INFERRED")},
        "dependents": {n: len(nx.descendants(d, n)) for n in d.nodes},
    }
