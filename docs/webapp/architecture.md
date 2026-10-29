# CryptoShift Web App v2: architecture

Status: PLANNED (design document; nothing here is built yet). Hackathon prototype for mentors and judges; not a
production banking product or a certification tool.

## The picture

```
 Your browser (http://127.0.0.1:8600)                      ── trust boundary A: the browser is untrusted ──
 ┌──────────────────────────────────────────────┐
 │ React 18 + TypeScript app (web/dist)          │  never sees provider keys; only the session cookie
 │  pages ── typed API client (openapi-typescript) ── TanStack Query cache            │
 └───────────────▲──────────────────────────────┘
                 │ HTTPS not needed on loopback; same-origin only (CORS: 127.0.0.1:8600 / Vite dev 127.0.0.1:5173)
                 │ cookie: cs_session (HttpOnly, SameSite=Strict) + header X-CSRF-Token
 ┌───────────────┴──────────────────────────────────────────────────────────────────┐
 │ FastAPI backend  src/cryptoshift/api/   (one process, bound to 127.0.0.1)          │
 │  middleware: request id → size limit → security headers + CSP → auth → CSRF → rate limit │
 │  routers:  /api/v1/reports/*  (read-only adapters, schema-validated)              │
 │            /api/v1/approvals   /api/v1/jobs   /api/v1/scans   /api/v1/assistant   │
 │            /api/v1/audit       /api/v1/settings   /api/v1/auth   /health /ready   │
 │  services: adapters ─ jobs runner (allow-list) ─ audit chain ─ assistant proxy     │
 │  storage:  SQLite (scratch/derived/webapp/app.db) via SQLAlchemy 2 + Alembic        │
 │            runs, jobs, approvals mirror, settings, users, audit log                 │
 └──────┬─────────────────────┬─────────────────────────┬─────────────────────────────┘
        │ reads (never writes) │ runs allow-listed scripts│ HTTP 127.0.0.1:8765
        ▼                      ▼                          ▼
  reports/member3/*.json   scripts/member3_pipeline.py   Member 3 assistant service (FastAPI)
  scratch/derived/*.json   scripts/inventory_v11.py ...  ── trust boundary B: owns SARVAM_API_KEY ──
  schemas/*.json           (no shell, timeout, redacted)   └─▶ api.sarvam.ai (only if cloud mode is ON)
  (Members 2 and 3)
                                                     ── trust boundary C: scanned files are hostile data ──
```

## Data flow, in plain words

1. **Members 2 and 3 produce the evidence.** Their scripts write JSON reports to `reports/` and to the git-ignored `scratch/derived/`.
2. **The backend reads those files and checks them.** It reads them through **read-only adapters** that validate each file against the published schemas (`schemas/`).
   - A missing file returns `status: "missing"` together with the command that produces it.
   - A schema mismatch returns `status: "schema_mismatch"` with the first errors.
   - An unknown status value becomes `"unknown"`, never "pass".
3. **The browser asks the backend, never the files.** The React app calls `/api/v1/...`. Every number on screen comes from those responses, and the evidence drawer shows each value's file, producer, time and SHA-256.
4. **Actions are jobs.** "Run" buttons create **jobs**. A job runs one script from a fixed allow-list (an argument list, no shell, a timeout), saves its redacted output, and then the reports are re-read ("run and reload").
5. **Approvals use Member 3's own rules.** The backend calls `cryptoshift.gates.approval.approve()`, so a step can be approved only if it is READY and every required gate passes. The record holds the name, the time and the plan hash. A plan change invalidates it.
6. **Everything that changes something is audited.** Each audit entry is chained to the previous one by SHA-256, and `/api/v1/audit/verify` recomputes the chain to detect tampering.
7. **The assistant is proxied.** The backend forwards questions to Member 3's assistant service on 127.0.0.1:8765, which alone holds the Sarvam key.
   - If that service is down, the backend answers in-process in **TEMPLATE_FALLBACK** mode (deterministic, no network).
   - Cloud use for custom scans defaults to **OFF**.

## Trust boundaries and controls

| Boundary | Risk | Controls |
|---|---|---|
| A: browser ↔ backend | cross-site requests, script injection, clickjacking | 127.0.0.1 bind; CORS limited to the local origin; SameSite=Strict HttpOnly session cookie + CSRF header token on every mutating request; CSP `default-src 'self'` (no inline scripts, no CDNs); `X-Frame-Options: DENY` and `frame-ancestors 'none'`; request size limit; rate limits; all scanned text returned as plain strings and rendered as text (React escapes) |
| B: backend ↔ assistant / Sarvam | key leakage, prompt injection | keys only in the assistant process environment; backend never reads provider keys; responses carry `mode`; Member 3's validator and local guard stay in front |
| C: scanned files | path traversal, secrets, huge files, code execution | allow-listed root folders from settings; resolve + reject `..` and symlinks leaving the root; text types only; size caps; never execute scanned code; never open `.env`, `qcloud.env`, `*.pem`, `*.key`, `*.p12`; explicit "I am authorized to scan this" acknowledgement written to the audit log; uploads go to a temp folder that is deleted after the scan |
| D: operator ↔ approval | software approving by itself | only the `approver` role, only one READY step at a time, typed name + typed plan hash; no "approve all"; the assistant has no approval tool |

## Roles

| Role | Can |
|---|---|
| viewer | read every page, verify the audit chain |
| analyst | viewer + run allow-listed jobs and scans, use the assistant |
| approver | analyst + approve a single READY step |

**Local mode:**
- There is a single organisation.
- Users are created with `python -m cryptoshift.api.admin create-user` (password hashed with stdlib `hashlib.scrypt`).
- The session-signing secret is generated with `secrets.token_bytes(32)` into the git-ignored `scratch/derived/webapp/session.secret`.

## Why these technologies (short)

- **FastAPI + Pydantic v2.** Typed request and response models, with free OpenAPI.
- **openapi-typescript** turns that OpenAPI into TypeScript types, so the frontend breaks at compile time if the API changes.
- **SQLite + SQLAlchemy 2 + Alembic.** A file database (nothing to install) and reproducible migrations.
- **itsdangerous** signs the session cookies (simple, no JWT pitfalls).
- **React + Vite + Tailwind + Radix.** Fast builds, a utility-CSS design system and accessible headless widgets (focus trap, keyboard).
- **TanStack Query / Table.** Caching, retries and sortable, virtualised tables.
- **Charts and graph:** Recharts for charts; Cytoscape.js for the dependency graph.
- **Fonts:** self-hosted through @fontsource, so the offline demo works without CDN calls.

## Deployment modes

| Mode | Command | Notes |
|---|---|---|
| Single-process demo | `scripts\run_full_demo.ps1` | backend serves `web/dist` on 127.0.0.1:8600 |
| Development | backend `uvicorn` on 127.0.0.1:8600 + `npm run dev` (Vite) on 127.0.0.1:5173 | Vite proxies `/api` to the backend |
| Offline demo | `?demo=1` / Settings → Demo mode | adapters read the frozen snapshot `scratch/derived/ui-snapshot/<stamp>/` |
| Docker | – | **PLANNED** (Docker not installed) |

Non-local deployment is out of scope.
