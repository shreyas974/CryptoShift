# Member 3 → Member 4 JSON contract

Schemas: `schemas/member3/*.schema.json` (JSON Schema 2020-12). Examples built from the real pipeline output and
validated in `tests/test_member3_contract.py`: `schemas/member3/examples/*.example.json`.
Regenerate: `.\.venv\Scripts\python.exe scripts/member3_pipeline.py` then `scripts/build_member3_contract.py`.

| Artefact | File | Schema |
|---|---|---|
| Migration plan (full) | `reports/member3/plan.json` (committed), `scratch/derived/member3/bundle/plan.json` | `plan.schema.json` (`schema_version = member3-plan/1.0`) |
| Gate results | `plan.steps` | `gate_results.schema.json` |
| Rollback record | `plan.rollback` | `rollback_record.schema.json` |
| Assistant API | `POST http://127.0.0.1:8765/ask` | `agent_api.schema.json` |

## Plan fields Member 4 should display

- `status_labels` — show next to every number (e.g. risk = "PROVISIONAL, UNVALIDATED").
- `services[*]`: `evidence_source` (`OBSERVED` / `DECLARED_ONLY`), `finding_ids`, `hold_finding_ids`,
  `candidate_targets` (strings starting with `HOLD` must be shown as held, not as a mapping), `risk.score`,
  `risk.reason`, `field_sources`.
- `edges[*]`: `provenance` (`OBSERVED` with `file`/`line`, `DECLARED`, `INFERRED` with `reason`).
- `graph_analysis`: `cycles`, `conflicts` (show conflicts prominently), `edge_counts`.
- `schedule`: `waves`, `objective`, `dependency_violations` (must be empty), `config` (assumptions).
- `steps[*]`: `state` (`PROPOSED` / `READY` / `APPROVED`), `gates[*]` (`status`, `evidence`, `reason`),
  `blocking_gates`, `evidence_scope` (always display: READY is generic loopback evidence).
- `rollback`: `restore`, `snapshot_sha256`, `trigger`, `rehearsal_result`, `warnings`.
- `approval`: `approved_steps`, `invalidated_approvals`, `plan_hash`.

## Rules for consumers

1. Never compute or change a PQC mapping in the UI; display `candidate_targets` as given.
2. Never offer an "approve" button that bypasses `scripts/approve_plan.py`; approvals need a named human and are
   bound to `plan_hash`. A changed plan invalidates earlier approvals.
3. Do not present `READY` as "verified in production" or "secure".
4. `scheduler_comparison.qaoa_simulator` is a SIMULATOR result; `qpiai_opt.authenticated_local_solve.status` is
   currently `BLOCKED`.
