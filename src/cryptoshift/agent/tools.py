"""Read-only tools over a CryptoShift Member 3 plan bundle (dict loaded from plan.json).

No tool writes files, approves plans, changes mappings, runs commands, touches .env or uses the network.
Every result carries the IDs that answers must cite.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional


class ReadOnlyTools:
    NAMES = ("list_findings", "get_task", "get_dependency_edges", "get_gate_results", "get_rollback_plan", "compare_schedulers")

    def __init__(self, bundle: Dict[str, Any]) -> None:
        self._b = copy.deepcopy(bundle)  # tools never see or mutate the caller's object

    # ------------------------------------------------------------------ helpers
    def services(self) -> List[str]:
        return sorted(self._b.get("services", {}))

    def finding_ids(self) -> List[str]:
        return [f["finding_id"] for f in self._b.get("findings", [])]

    def valid_ids(self) -> set:
        ids = set(self.finding_ids())
        ids |= {f"task:{s}" for s in self.services()}
        ids |= {s["step_id"] for s in self._b.get("steps", [])}
        ids |= {f"gate:{s['step_id']}:{g['gate']}" for s in self._b.get("steps", []) for g in s["gates"]}
        ids |= {self.edge_id(e) for e in self._b.get("edges", [])}
        rb = self._b.get("rollback") or {}
        if rb.get("snapshot_sha256"):
            ids.add(f"rollback:{rb['snapshot_sha256'][:12]}")
        ids |= {"scheduler:baseline", "scheduler:qpiai_opt", "scheduler:qaoa_simulator"}
        return ids

    @staticmethod
    def edge_id(e: Dict[str, Any]) -> str:
        return f"edge:{e['upstream']}->{e['downstream']}:{e['provenance']}"

    # ------------------------------------------------------------------ tools
    def list_findings(self, service: Optional[str] = None) -> List[Dict[str, Any]]:
        out = []
        for f in self._b.get("findings", []):
            if service and f["service_id"] != service:
                continue
            out.append({"id": f["finding_id"], "service": f["service_id"], "file": f["file_path"], "line": f["line_number"],
                         "algorithm": f["legacy_algorithm"], "purpose": f["operation_purpose"], "ambiguity": f.get("ambiguity", "none"),
                         "candidate": f["target_pqc_algorithm"], "snippet_data": f.get("snippet_redacted", "")})
        return out

    def get_task(self, service: str) -> Optional[Dict[str, Any]]:
        s = self._b.get("services", {}).get(service)
        if not s:
            return None
        wave = (self._b.get("schedule") or {}).get("task_to_wave", {}).get(service)
        return {"id": f"task:{service}", "evidence_source": s["evidence_source"], "finding_ids": s["finding_ids"],
                "hold_finding_ids": s["hold_finding_ids"], "candidates": s["candidate_targets"], "risk": s["risk"]["score"],
                "risk_label": s["risk"]["label"], "risk_reason": s["risk"]["reason"], "wave": wave,
                "field_sources": s["field_sources"]}

    def get_dependency_edges(self, service: Optional[str] = None) -> List[Dict[str, Any]]:
        return [{"id": self.edge_id(e), **{k: e[k] for k in ("upstream", "downstream", "provenance", "file", "line", "reason")}}
                for e in self._b.get("edges", []) if not service or service in (e["upstream"], e["downstream"])]

    def get_gate_results(self, service: Optional[str] = None) -> List[Dict[str, Any]]:
        return [{"id": s["step_id"], "service": s["service_id"], "state": s["state"], "blocking": s["blocking_gates"],
                 "gates": [{"id": f"gate:{s['step_id']}:{g['gate']}", **g} for g in s["gates"]],
                 "scope": s.get("evidence_scope", "")}
                for s in self._b.get("steps", []) if not service or s["service_id"] == service]

    def get_rollback_plan(self) -> Optional[Dict[str, Any]]:
        rb = self._b.get("rollback")
        if not rb or not rb.get("snapshot_sha256"):
            return None
        return {"id": f"rollback:{rb['snapshot_sha256'][:12]}", **rb}

    def compare_schedulers(self) -> Optional[Dict[str, Any]]:
        c = self._b.get("scheduler_comparison")
        return copy.deepcopy(c) if c else None

    def approval(self) -> Dict[str, Any]:
        return copy.deepcopy(self._b.get("approval", {}))
