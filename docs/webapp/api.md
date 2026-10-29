# CryptoShift API v1 (contract)

Status: PLANNED. The FastAPI app will publish the same contract as OpenAPI at `/api/v1/openapi.json`, with
interactive docs at `/api/docs`. TypeScript types are generated from that file into `web/src/api/schema.d.ts`.

## Conventions

- **Base path and format:** base path `/api/v1`. JSON only. The request size limit is 1 MiB, or 5 MiB for scan uploads.
- **Sessions:** `cs_session` (HttpOnly, SameSite=Strict, Path=/) plus `cs_csrf` (readable by JS). Every `POST/PUT/PATCH/DELETE` must send the header `X-CSRF-Token` equal to `cs_csrf`; otherwise the response is `403 csrf_failed`.
- **Errors:** every error is `{"error": {"code": "...", "message": "...", "request_id": "..."}}`. The codes are `unauthenticated` (401), `forbidden` (403), `csrf_failed` (403), `not_found` (404), `validation_error` (422), `rate_limited` (429), `payload_too_large` (413), `not_ready` (409), `upstream_unavailable` (503).
- **Report envelope:** every report response wraps its data in a `Sourced` envelope:

  ```json
  {"status": "ok|missing|schema_mismatch|error", "data": {...} | null,
   "source": {"file": "reports/member3/plan.json", "producer": "Member 3 pipeline", "label": "VERIFIED on SYNTHETIC demo bank",
              "modified": "2026-10-29T16:40:12", "sha256": "…", "command": "scripts/member3_pipeline.py", "mode": "LIVE|DEMO"},
   "errors": []}
  ```

- **Status values:** they are normalised to `VERIFIED, PARTIAL, MOCKED, SIMULATED, SYNTHETIC, PLANNED, BLOCKED, PASS, FAIL, READY, PROPOSED, APPROVED, RUN, OBSERVED, DECLARED, INFERRED, HOLD`. Anything else becomes `unknown`.
- **Scanned text:** snippets, file names and rationale are returned as plain strings capped at 160 characters (500 for rationale), with control characters removed. The UI renders them as text, never as HTML.
- **Audit:** every mutating request is audited (actor, role, action, target, result, request id), whether it succeeds or fails.

## Endpoints

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/health` | none | liveness: `{"status":"ok"}` |
| GET | `/ready` | none | DB reachable, migrations at head, data dir readable, assistant reachable (bool) |
| POST | `/api/v1/auth/login` | none | `{username, password}` sets the session and CSRF cookies; rate limited (5/min) |
| POST | `/api/v1/auth/logout` | any | clears the session |
| GET | `/api/v1/auth/me` | any | `{username, role, csrf}` |
| GET | `/api/v1/overview` | viewer | pipeline stages (each with status + source), key counts, plan hash, data mode |
| GET | `/api/v1/reports/{key}` | viewer | raw `Sourced` report; key ∈ `plan, inventory, relationships_fixture, verification, scheduling, ml_cesnet, ml_triage, agent_eval, agent_eval_sarvam, eval_calibration, eval_calibration2, eval_held_out, eval_cryptoapi, registry, claims` |
| GET | `/api/v1/findings?service=&purpose=&detector=&hold=` | viewer | findings table rows (escaped and capped) |
| GET | `/api/v1/graph` | viewer | nodes, edges (with provenance, kind, file:line), unknown endpoints, conflicts, cycles |
| GET | `/api/v1/plan` | viewer | waves, tasks (risk + "provisional, not validated" label), scheduler comparison (baseline / QpiAI Opt / QCloud SIMULATOR) |
| GET | `/api/v1/verification` | viewer | gate matrix, compatibility matrix (incl. negative cases), traces, overhead + environment |
| GET | `/api/v1/approvals` | viewer | steps with state, blocking gates, approval records (valid / INVALIDATED) |
| POST | `/api/v1/approvals` | **approver** | `{step_id, approver_name, plan_hash_prefix}` (one step only). Returns 409 `not_ready` unless READY and all required gates PASS and the prefix (≥12 characters) matches the current plan hash. Calls `gates.approval.approve()`. |
| GET | `/api/v1/rollback` | viewer | rollback record and rehearsal result, with the SHA-1/3DES warning |
| GET | `/api/v1/evaluation` | viewer | detection sets kept separate (calibration, calibration-2, held-out round 2, synthetic smoke test, CryptoAPI-Bench) |
| GET | `/api/v1/ml` | viewer | track A/B metrics beside baselines, with notices |
| GET | `/api/v1/sources` | viewer | dataset registry and pinned public repos |
| GET | `/api/v1/claims` | viewer | claims register (Markdown text) and the "must not claim" list |
| POST | `/api/v1/assistant/ask` | analyst | `{question}` returns `{answer, citations, mode, mode_reason, usage, refused}`; rate limited (10/min) |
| GET | `/api/v1/assistant/status` | viewer | mode, cloud ON/OFF, `key_configured` (bool from the assistant's /health; never the key), usage counters |
| GET | `/api/v1/jobs/commands` | analyst | the allow-list (`id`, `label`, `timeout_s`) |
| POST | `/api/v1/jobs` | analyst | `{command_id}` returns a job; 422 if not allow-listed |
| GET | `/api/v1/jobs/{id}` | analyst | status `queued/running/succeeded/failed/timeout`, progress, redacted output tail |
| POST | `/api/v1/scans` | analyst | `{root_id, subpath, authorized: true}` or multipart upload (≤5 MiB, text types). Validates the root / traversal / symlinks, then starts a scan job. |
| GET | `/api/v1/audit?limit=&offset=` | viewer | audit entries (newest first) |
| GET | `/api/v1/audit/verify` | viewer | `{valid: bool, entries: n, first_bad_id: null|int}` |
| GET | `/api/v1/settings` | viewer | data mode, scan roots, cloud_for_custom_scans (default false), theme default |
| PUT | `/api/v1/settings` | **approver** | update settings (audited) |
| GET | `/api/v1/export/{fmt}?page=` | viewer | `md` or `json` export of a page's data (Tier 2) |

## Database (SQLite, Alembic migration `0001_initial`)

| Table | Columns |
|---|---|
| `users` | id, username (unique), password_hash (scrypt), role (`viewer`/`analyst`/`approver`), created_at, disabled |
| `audit_log` | id, ts, request_id, actor, role, action, target, result, detail_json, prev_hash, entry_hash. **Append-only:** SQLite triggers abort UPDATE and DELETE. `entry_hash = sha256(prev_hash ‖ canonical_json(entry))`. |
| `jobs` | id, command_id, args_json, status, progress, started_at, finished_at, exit_code, output_tail (redacted, ≤8 KB), created_by |
| `runs` | id, job_id, report_key, sha256_before, sha256_after, created_at (run-and-reload history) |
| `approvals_mirror` | id, step_id, approver_name, plan_hash, approved_at, valid (re-checked on read). Member 3's JSON store stays the source of truth. |
| `settings` | key, value_json, updated_by, updated_at |

## Job allow-list (exact argument lists, no shell, cwd = repo root)

| id | argv | timeout |
|---|---|---|
| `inventory_demo` | `python scripts/inventory_v11.py --path demo_bank_app/configs --cyclonedx` | 300 s |
| `inventory_fixture` | `python scripts/inventory_v11.py --path tests/fixtures/multiservice_bank --cyclonedx` | 300 s |
| `pipeline` | `python scripts/member3_pipeline.py` | 300 s |
| `agent_eval_template` | `python scripts/evaluate_agent.py` | 300 s |
| `snapshot` | `python scripts/ui_snapshot.py` | 120 s |
| `scan_root` | `python scripts/inventory_v11.py --path <validated path> --out-dir scratch/derived/webapp/scans/<job>` | 300 s |

Not in the allow-list (never runnable from the web): `--mode sarvam`, `--authorize-local-solve`, `approve_plan.py`, `pip`, `git`, `openssl`.

## Rate limits (in-memory token buckets, per session; per IP for login)

login 5/min · assistant 10/min · jobs and scans 6/min · approvals 6/min · settings 6/min.
