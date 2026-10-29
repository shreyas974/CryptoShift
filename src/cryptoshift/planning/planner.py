"""From scanner findings to a migration plan (Member 3).

findings -> per-service tasks (finding_ids kept as evidence) -> provenance dependency graph -> provisional risk
score -> constrained wave schedule (existing deterministic scheduler, via an adapter) -> sensitivity analysis.
Every field records where its value came from: OBSERVED (scanned file), DECLARED (synthetic descriptor) or
ASSUMPTION (planning_config.json defaults).
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cryptoshift.models import CryptoFinding, MigrationTask, WaveScheduleConfig
from cryptoshift.optimization.auth_check import PROJECT_ROOT
from cryptoshift.optimization.fallback_scheduler import is_schedule_feasible, solve_with_fallback_scheduler
from cryptoshift.dependencies import validate_dependency_order
from cryptoshift.planning.dependency_graph import (
    analyse_graph, build_graph, constraint_digraph, declared_edges, observed_edges,
)
from cryptoshift.planning.findings import collect_findings, family_group, load_config
from cryptoshift.planning.risk import rank, score_service
from cryptoshift.rules import resolve_contextual_pqc_rule

DEFAULT_TARGET = PROJECT_ROOT / "demo_bank_app" / "configs"
LISTENER_HINTS = ("listen ", "tls_listener", "server_name", "ssl_certificate")


def _descriptor() -> Dict[str, Dict[str, Any]]:
    from demo_bank_app.services import SYNTHETIC_BANK_SERVICES

    return copy.deepcopy(SYNTHETIC_BANK_SERVICES)


def candidate_for(f: CryptoFinding) -> str:
    """Purpose-dependent candidate; unknown purpose is always HOLD (never a PQC mapping)."""
    if f.operation_purpose == "unknown":
        return resolve_contextual_pqc_rule(f.legacy_algorithm, "unknown")["target_pqc"]
    return f.target_pqc_algorithm


def _yaml_meta(files: List[str], abs_paths: Dict[str, Path]) -> Dict[str, Any]:
    import yaml

    out: Dict[str, Any] = {}
    for rel in files:
        if rel.endswith((".yaml", ".yml")):
            data = yaml.safe_load(abs_paths[rel].read_text(encoding="utf-8")) or {}
            for k in ("criticality", "verification_ready_wave0", "data_retention_years"):
                if k in data:
                    out[k] = (data[k], rel)
    return out


def build_problem(target: Optional[Path] = None, include_declared: bool = True,
                  cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build services, findings, graph and scored tasks (no scheduling)."""
    cfg = cfg or load_config()
    target = Path(target or DEFAULT_TARGET)
    findings, scanned = collect_findings(target)
    descriptor = _descriptor() if include_declared else {}
    known = set(scanned) | set(descriptor)

    abs_paths = {rel: ap for m in scanned.values() for rel, ap in m["_abs"].items()}
    file_service = {f: s for s, m in scanned.items() for f in m["files"]}
    files = [abs_paths[f] for f in file_service]
    obs = observed_edges(files, file_service, known)
    edges = obs["edges"] + declared_edges({k: v for k, v in descriptor.items()})
    graph = build_graph(sorted(known), edges)
    analysis = analyse_graph(graph, cfg["enforced_edge_provenance"])
    max_dep = max(analysis["dependents"].values() or [1]) or 1

    by_service: Dict[str, List[CryptoFinding]] = defaultdict(list)
    for f in findings:
        by_service[f.service_id].append(f)

    services: Dict[str, Dict[str, Any]] = {}
    for sid in sorted(known):
        svc_findings = [f for f in by_service.get(sid, []) if f.severity != "INFO"]
        desc = descriptor.get(sid, {})
        files_s = scanned.get(sid, {}).get("files", [])
        ymeta = _yaml_meta(files_s, abs_paths)
        sources: Dict[str, str] = {}

        def pick(key: str, default: Any) -> Any:
            if key in ymeta:
                sources[key] = f"OBSERVED ({ymeta[key][1]})"
                return ymeta[key][0]
            if key in desc:
                sources[key] = "DECLARED (demo_bank_app/services.py)"
                return desc[key]
            sources[key] = "ASSUMPTION (planning_config.json default)"
            return default

        criticality = pick("criticality", "unknown")
        ready = bool(pick("verification_ready_wave0", False))
        duration = int(pick("duration_minutes", cfg["default_duration_minutes"]))
        cost = float(pick("rollout_cost", cfg["default_rollout_cost"]))

        if svc_findings:
            pairs = [(family_group(f), f.operation_purpose) for f in svc_findings]
            legacy = sorted({f.legacy_algorithm for f in svc_findings})
            evidence = "OBSERVED"
        else:
            pairs = [(family_group(CryptoFinding("", "", "", 0, a, "", "", "", "", algorithm_family=a)), "unknown")
                     for a in desc.get("legacy_algorithms", [])]
            legacy = list(desc.get("legacy_algorithms", []))
            evidence = "DECLARED_ONLY" if desc else "NONE"
        if files_s:
            text = " ".join(abs_paths[f].read_text(encoding="utf-8", errors="replace") for f in files_s)
            exposure = "observed_listener" if any(h in text for h in LISTENER_HINTS) else "none_observed"
        else:
            exposure = "unknown"

        holds = [f.finding_id for f in svc_findings if f.operation_purpose == "unknown"]
        targets = sorted({f"{candidate_for(f)} [{f.operation_purpose}]" for f in svc_findings}) or [
            "HOLD: no scanned evidence; algorithms only DECLARED in synthetic descriptor (purpose unverified)"
        ]
        features = {
            "group_purpose_pairs": pairs,
            "network_exposure": exposure,
            "criticality": criticality,
            "dependents_norm": analysis["dependents"].get(sid, 0) / max_dep,
            "verification_ready_wave0": ready,
        }
        services[sid] = {
            "service_id": sid,
            "evidence_source": evidence,
            "finding_ids": [f.finding_id for f in svc_findings],
            "hold_finding_ids": holds,
            "files": files_s,
            "legacy_algorithms": legacy,
            "candidate_targets": targets,
            "duration_minutes": duration,
            "rollout_cost": cost,
            "criticality": criticality,
            "verification_ready_wave0": ready,
            "field_sources": sources,
            "features": features,
            "risk": score_service(features, cfg),
        }

    return {
        "target": str(target.resolve().relative_to(PROJECT_ROOT).as_posix()) if target.resolve().is_relative_to(PROJECT_ROOT) else target.name,
        "config": cfg,
        "findings": findings,
        "services": services,
        "edges": edges,
        "unknown_endpoints": obs["unknown_endpoints"],
        "graph": graph,
        "graph_analysis": analysis,
    }


def to_tasks(problem: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None,
             scores: Optional[Dict[str, float]] = None) -> Tuple[List[MigrationTask], List[Dict[str, Any]]]:
    """MigrationTask records for the scheduler; dependencies = enforced edges inside the task set."""
    cfg = cfg or problem["config"]
    d = constraint_digraph(problem["graph"], cfg["enforced_edge_provenance"])
    ids = set(problem["services"])
    tasks, outside = [], []
    for sid, s in sorted(problem["services"].items()):
        deps = sorted(u for u in d.predecessors(sid) if u in ids)
        outside += [{"service": sid, "dependency": u} for u in d.predecessors(sid) if u not in ids]
        tasks.append(MigrationTask(
            service_id=sid, name=sid, legacy_algorithms=s["legacy_algorithms"],
            target_algorithms=s["candidate_targets"], dependencies=deps,
            duration_minutes=s["duration_minutes"], rollout_cost=s["rollout_cost"],
            risk_score=(scores or {}).get(sid, s["risk"]["score"]),
            verification_ready_wave0=s["verification_ready_wave0"],
            criticality=str(s["criticality"]),
        ))
    return tasks, outside


def schedule(problem: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None,
             scores: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Adapter onto the existing deterministic scheduler, with constraint checks."""
    cfg = cfg or problem["config"]
    c = cfg["constraints"]
    wcfg = WaveScheduleConfig(num_waves=c["num_waves"], max_services_per_wave=c["max_services_per_wave"],
                              max_minutes_per_wave=c["max_minutes_per_wave"], risk_delay_weight=c["risk_delay_weight"],
                              enforce_verification_gate=c["enforce_verification_gate"])
    tasks, outside = to_tasks(problem, cfg, scores)
    if c["num_waves"] ** len(tasks) > 5_000_000:
        raise ValueError(f"Exhaustive baseline too large ({len(tasks)} services); reduce scope or use the MILP model")
    res = solve_with_fallback_scheduler(tasks, wcfg)
    dep_ok, dep_viol = validate_dependency_order(tasks, res.task_to_wave) if res.feasible else (False, ["infeasible"])
    feas_ok, feas_viol = is_schedule_feasible(tasks, res.task_to_wave, wcfg) if res.feasible else (False, ["infeasible"])
    return {
        "solver": res.solver_name, "feasible": res.feasible, "objective": res.objective_value,
        "task_to_wave": res.task_to_wave, "waves": {str(k): v for k, v in res.waves.items()},
        "runtime_seconds": res.runtime_seconds, "diagnostics": res.diagnostics,
        "dependency_violations": dep_viol if res.feasible else [], "constraint_violations": feas_viol if res.feasible else [],
        "dependencies_outside_task_set": outside, "config": c,
        "tasks": [t.to_dict() for t in tasks],
    }


def sensitivity(problem: Dict[str, Any], factors: Tuple[float, ...] = (0.5, 1.5)) -> Dict[str, Any]:
    """Vary each risk weight by the given factors; record rank and schedule changes (real re-runs)."""
    base_cfg = problem["config"]
    base_scores = {s: v["risk"]["score"] for s, v in problem["services"].items()}
    base_rank = rank(base_scores)
    base_sched = schedule(problem)["task_to_wave"]
    runs = []
    for wname in base_cfg["risk_weights"]:
        for fac in factors:
            cfg = copy.deepcopy(base_cfg)
            cfg["risk_weights"][wname] *= fac
            scores = {s: score_service(v["features"], cfg)["score"] for s, v in problem["services"].items()}
            r = rank(scores)
            sched = schedule(problem, cfg, scores)["task_to_wave"]
            runs.append({
                "weight": wname, "factor": fac, "rank": r, "rank_changed": r != base_rank,
                "kendall_tau": _kendall_tau(base_rank, r),
                "schedule_changed": sched != base_sched, "task_to_wave": sched,
            })
    n = len(runs)
    return {
        "base_rank": base_rank, "base_task_to_wave": base_sched, "runs": runs, "n_runs": n,
        "rank_changed_runs": sum(r["rank_changed"] for r in runs),
        "schedule_changed_runs": sum(r["schedule_changed"] for r in runs),
        "min_kendall_tau": min(r["kendall_tau"] for r in runs) if runs else None,
    }


def _kendall_tau(a: List[str], b: List[str]) -> float:
    pos = {x: i for i, x in enumerate(b)}
    n = len(a)
    if n < 2:
        return 1.0
    conc = disc = 0
    for i in range(n):
        for j in range(i + 1, n):
            if pos[a[i]] < pos[a[j]]:
                conc += 1
            else:
                disc += 1
    return round((conc - disc) / (conc + disc), 4)


def plan_hash(plan: Dict[str, Any]) -> str:
    """SHA-256 over the canonical JSON of the plan's decision content (used by the approval gate)."""
    core = {k: plan[k] for k in ("services", "edges", "schedule") if k in plan}
    return hashlib.sha256(json.dumps(core, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def problem_to_json(problem: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-serialisable view (findings as dicts, graph omitted)."""
    return {
        "target": problem["target"],
        "findings": [f.to_dict() for f in problem["findings"]],
        "services": problem["services"],
        "edges": problem["edges"],
        "unknown_endpoints": problem["unknown_endpoints"],
        "graph_analysis": problem["graph_analysis"],
        "config_status": problem["config"]["status"],
    }
