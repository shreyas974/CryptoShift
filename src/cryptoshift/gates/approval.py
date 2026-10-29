"""Human approval gate: PROPOSED -> READY (all required gates PASS) -> APPROVED (human CLI only).

Approval records hold approver name, UTC timestamp and the SHA-256 of the plan's decision content. Any change to
the plan after approval changes the hash and invalidates the approval. Software (pipeline, agent) never approves;
tests use the obviously fake approver "TEST-ONLY".
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from cryptoshift.planning.planner import plan_hash


class ApprovalError(ValueError):
    pass


def approve(plan: Dict[str, Any], step_ids: List[str], approver: str, store: Path) -> Dict[str, Any]:
    """Record a human approval for READY steps. Refuses non-READY steps and empty approver names."""
    if not approver or not approver.strip():
        raise ApprovalError("approver name is required")
    states = {s["step_id"]: s["state"] for s in plan["steps"]}
    unknown = [s for s in step_ids if s not in states]
    not_ready = [s for s in step_ids if s in states and states[s] != "READY"]
    if unknown or not_ready:
        raise ApprovalError(f"cannot approve: unknown={unknown} not_ready={not_ready}")
    rec = {"approver": approver.strip(), "approved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "plan_hash": plan_hash(plan), "step_ids": sorted(step_ids)}
    store.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(store.read_text(encoding="utf-8")) if store.is_file() else []
    existing.append(rec)
    store.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return rec


def approval_status(plan: Dict[str, Any], store: Path) -> Dict[str, Any]:
    """Apply stored approvals to the plan; approvals whose hash no longer matches are INVALIDATED."""
    current = plan_hash(plan)
    records = json.loads(store.read_text(encoding="utf-8")) if store.is_file() else []
    approved, invalid = set(), []
    for r in records:
        if r["plan_hash"] == current:
            approved.update(r["step_ids"])
        else:
            invalid.append({**r, "status": "INVALIDATED (plan changed after approval)"})
    for s in plan["steps"]:
        if s["step_id"] in approved and s["state"] == "READY":
            s["state"] = "APPROVED"
    return {"plan_hash": current, "approved_steps": sorted(approved), "invalidated_approvals": invalid,
            "records": len(records)}
