# CryptoShift web app v2

A local, single-organisation console for the CryptoShift PQC-01 hackathon prototype. It is **not** a production banking
product or a certification tool. It reads the real outputs of Members 2 and 3 through a FastAPI backend and shows them
in a React app (v2.1 design: dark plum canvas with purple and orange glow, top bar with drop-down menus, a code-drawn
glowing sphere hero, three-up cards, news-style lists and a gradient footer) plus an isometric explanatory figure
(Fig. 1, built with the anatomy skill). You can also upload your own dataset and run a pipeline on it. Everything binds to **127.0.0.1**.

## Install (inside the repo's `.venv` and `web/` only)

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-member3.txt -r requirements-api.txt
cd web; npm ci; npm run build; cd ..
$env:PYTHONPATH = "src"   # the admin module lives in src/
.\.venv\Scripts\python.exe -m cryptoshift.api.admin create-user <your-name> approver   # password typed at a hidden prompt
```

After the first account exists, approvers add everyone else in the app: **Admin → Users & roles**.

Roles:
- `viewer`: reads everything.
- `analyst`: also uploads datasets and runs pipelines, runs allow-listed jobs and scans, and asks the assistant.
- `approver`: also approves one READY step at a time, manages users, deletes runs and changes settings.

## Analyse your own dataset (Pipelines → Datasets & runs)

1. Choose a folder, or drop a `.zip` or files (20 MB limit). A folder or zip keeps the folder structure, which service detection uses.
2. Pick a pipeline: **Discovery** (inventory, relationships, CBOM-like + CycloneDX), **Discovery + migration plan**
   (adds services, dependencies, schedule and gates), or **Full** (re-runs the OpenSSL 3.5 loopback lab first; slow).
3. Tick the authorization box and press **Upload and run**. Watch the stages, then browse findings, services, steps
   and dependencies, and download every output (`.json`, `.md`).

Only text files are kept; `.env`, keys, keystores, symlinks and paths that leave the folder are refused or skipped.
Each run lives in `scratch/derived/webapp/runs/run-<id>/` (git-ignored) and never changes the shared reports.
The Member 3 scheduler refuses datasets with more than 15 services ("Exhaustive baseline too large"); the run then
shows the plan stage as FAIL with that message.

## Run

| Mode | Command | Open |
|---|---|---|
| Single-process demo | `powershell -ExecutionPolicy Bypass -File scripts\run_full_demo.ps1 start` (`stop`, `status`) | http://127.0.0.1:8600 |
| Development | backend: `.\.venv\Scripts\python.exe -m uvicorn --factory cryptoshift.api.main:app_factory --host 127.0.0.1 --port 8600`; frontend: `cd web; npm run dev` | http://127.0.0.1:5173 |
| Offline demo | Settings → Data mode → DEMO (reads the frozen snapshot from `scripts/ui_snapshot.py`; jobs and approvals are disabled) | same |
| API docs | – | http://127.0.0.1:8600/api/docs |

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests          # existing suites (100)
.\.venv\Scripts\python.exe -m pytest tests/test_webapp_api.py -q   # backend API (20 + 1 skipped)
.\.venv\Scripts\python.exe -m ruff check --config ruff-api.toml src/cryptoshift/api tests/test_webapp_api.py
cd web
npx tsc -b --noEmit; npx eslint . --max-warnings 0; npx prettier --check "src/**/*.{ts,tsx,css}"
npx vitest run           # components + figure + automated contrast test (30)
npx playwright test      # E2E + axe on 16 pages x 2 themes, upload, users (9); uses the installed Chrome, no browser download
```

Regenerate the API types after changing the backend:

```powershell
$env:PYTHONPATH = "src"; .\.venv\Scripts\python.exe -m cryptoshift.api.admin export-openapi web/openapi.json; cd web; npm run gen:api
```

## Folder map

| Path | What |
|---|---|
| `src/cryptoshift/api/` | FastAPI app (`main.py`), security (`security.py`), audit chain (`audit.py`), adapters/jobs/scans/assistant proxy (`services.py`), SQLite + Alembic (`db.py`, `migrations/`), user admin (`admin.py`) |
| `web/src/` | React app: `App.tsx` (shell, routing), `pages/tier1.tsx`, `pages/tier2.tsx`, `components/` (badges, tables, drawers, palette, background), `components/PipelineFigure.tsx` + `components/pipeline/` (Fig. 1), `components/iso/` (vendored anatomy kit, MIT), `api/` (typed client and generated `schema.d.ts`), `styles/index.css` (tokens) |
| `web/e2e/` | Playwright tests and the isolated test backend (`serve_e2e.py`, port 8611, temp DB) |
| `docs/webapp/` | architecture, API, design, wireframe, screens, runbook, parity, handoff |
| `scratch/derived/webapp/` | git-ignored runtime state: `app.db`, `session.secret`, server logs, test outputs |

## Troubleshooting

- **"Backend not reachable":** start it with `run_full_demo.ps1 start`, then look at `scratch\derived\webapp\server.err`.
- **"No local accounts yet":** run `create-user` (see Install).
- **"File missing" cards:** the backend says which command produces the file. Run it, or use the Overview "Run and reload" card as an analyst.
- **429 rate limit:** wait a minute. Login allows 5 per minute; the assistant 10; jobs, scans/uploads, approvals, settings and user changes 6.
- **"No module named cryptoshift"** when running `admin`: set `$env:PYTHONPATH = "src"` first.
- **The assistant answers in TEMPLATE_FALLBACK:** Member 3's assistant service isn't running. This is expected and safe: nothing leaves the machine.
