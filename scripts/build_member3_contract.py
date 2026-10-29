#!/usr/bin/env python3
"""Write JSON Schemas for the Member 3 contract and example files built from the real pipeline output.

Outputs: schemas/member3/*.schema.json and schemas/member3/examples/*.json (validated with jsonschema).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from cryptoshift import member3_pipeline as pipe  # noqa: E402
from cryptoshift.agent.assistant import Assistant  # noqa: E402

OUT = ROOT / "schemas" / "member3"
STR, INT, NUM, BOOL = {"type": "string"}, {"type": "integer"}, {"type": "number"}, {"type": "boolean"}
NSTR = {"type": ["string", "null"]}
ARR_STR = {"type": "array", "items": STR}

GATE = {"type": "object", "required": ["gate", "status", "evidence", "reason"], "additionalProperties": False,
        "properties": {"gate": STR, "status": {"enum": ["PASS", "FAIL", "BLOCKED"]}, "evidence": STR, "reason": STR}}
STEP = {"type": "object", "required": ["step_id", "service_id", "purposes", "gates", "state", "blocking_gates", "evidence_scope"],
        "properties": {"step_id": {"type": "string", "pattern": "^migrate:"}, "service_id": STR, "purposes": ARR_STR,
                       "gates": {"type": "array", "items": GATE}, "state": {"enum": ["PROPOSED", "READY", "APPROVED"]},
                       "blocking_gates": ARR_STR, "evidence_scope": STR}}
EDGE = {"type": "object", "required": ["upstream", "downstream", "provenance", "file", "line", "reason"],
        "properties": {"upstream": STR, "downstream": STR, "provenance": {"enum": ["OBSERVED", "DECLARED", "INFERRED"]},
                       "file": NSTR, "line": {"type": ["integer", "null"]}, "reason": STR, "evidence": STR}}
SERVICE = {"type": "object", "required": ["service_id", "evidence_source", "finding_ids", "hold_finding_ids", "candidate_targets",
                                          "duration_minutes", "verification_ready_wave0", "field_sources", "risk"],
           "properties": {"service_id": STR, "evidence_source": {"enum": ["OBSERVED", "DECLARED_ONLY", "NONE"]},
                          "finding_ids": ARR_STR, "hold_finding_ids": ARR_STR, "candidate_targets": ARR_STR,
                          "duration_minutes": INT, "verification_ready_wave0": BOOL, "field_sources": {"type": "object"},
                          "risk": {"type": "object", "required": ["score", "contributions", "reason", "label"],
                                   "properties": {"score": NUM, "reason": STR, "label": {"const": "PROVISIONAL, UNVALIDATED"}}}}}
ROLLBACK = {"type": "object", "required": ["label", "restore", "snapshot_sha256", "trigger", "recovery_check", "rehearsal_result", "warnings"],
            "properties": {"label": STR, "profile": NSTR, "restore": STR, "snapshot_sha256": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
                           "trigger": NSTR, "recovery_check": STR, "recovery_command": NSTR,
                           "rehearsal_result": {"type": "object", "properties": {k: {"type": ["boolean", "null"]} for k in
                                                ("forced_failure_detected", "restored_hash_matches_snapshot", "recovered", "originals_unchanged")}},
                           "warnings": ARR_STR, "applies_to_steps": ARR_STR}}
PLAN = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "CryptoShift Member 3 migration plan",
        "type": "object",
        "required": ["schema_version", "generated_at_utc", "status_labels", "target", "findings", "services", "edges", "graph_analysis",
                     "schedule", "steps", "rollback", "plan_hash", "approval"],
        "properties": {"schema_version": {"const": pipe.SCHEMA_VERSION}, "generated_at_utc": STR, "status_labels": {"type": "object"},
                       "target": STR, "findings": {"type": "array", "items": {"type": "object", "required": ["finding_id", "service_id", "file_path", "line_number", "operation_purpose"]}},
                       "services": {"type": "object", "additionalProperties": SERVICE}, "edges": {"type": "array", "items": EDGE},
                       "graph_analysis": {"type": "object", "required": ["cycles", "conflicts", "edge_counts"]},
                       "schedule": {"type": "object", "required": ["feasible", "objective", "task_to_wave", "waves", "dependency_violations"]},
                       "steps": {"type": "array", "items": STEP}, "rollback": ROLLBACK,
                       "plan_hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                       "approval": {"type": "object", "required": ["plan_hash", "approved_steps", "invalidated_approvals"]}}}
GATES = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Gate results (list of plan steps)", "type": "array", "items": STEP}
ROLLBACK_DOC = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Rollback record", **ROLLBACK}
AGENT = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "CryptoShift Assistant API (POST /ask)",
         "type": "object", "properties": {
             "request": {"type": "object", "required": ["question"], "properties": {"question": STR}, "additionalProperties": False},
             "response": {"type": "object", "required": ["answer", "citations", "tools_used", "refused", "backend", "mode"],
                          "properties": {"answer": STR, "citations": ARR_STR, "tools_used": ARR_STR, "refused": BOOL, "backend": STR,
                                         "mode": {"enum": ["SARVAM_CLOUD", "TEMPLATE_FALLBACK"]},
                                         "mode_reason": STR, "validator": STR,
                                         "usage": {"type": "object", "properties": {"prompt_tokens": {"type": "integer"},
                                                                                    "completion_tokens": {"type": "integer"}}}}}},
         "required": ["request", "response"]}


def main() -> int:
    import jsonschema

    plan = json.loads((pipe.DERIVED / "bundle" / "plan.json").read_text(encoding="utf-8"))
    (OUT / "examples").mkdir(parents=True, exist_ok=True)
    schemas = {"plan": PLAN, "gate_results": GATES, "rollback_record": ROLLBACK_DOC, "agent_api": AGENT}
    q = "Which gates block ledger_audit?"
    examples = {
        "plan": {k: plan[k] for k in PLAN["required"]} | {"findings": plan["findings"][:3], "schema_version": plan["schema_version"]},
        "gate_results": plan["steps"],
        "rollback_record": plan["rollback"],
        "agent_api": {"request": {"question": q}, "response": Assistant(plan).answer(q)},
    }
    for name, schema in schemas.items():
        jsonschema.validate(examples[name], schema)
        (OUT / f"{name}.schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
        (OUT / "examples" / f"{name}.example.json").write_text(json.dumps(examples[name], indent=2, default=str), encoding="utf-8")
        print(f"{name}: example validates against schema")
    return 0


if __name__ == "__main__":
    sys.exit(main())
