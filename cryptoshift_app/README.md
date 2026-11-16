# CryptoShift

Verification-gated post-quantum cryptographic migration for banking applications.
Built for **Quant-A-Maze 3.0 — PQC-01: Verification-Gated Cryptographic Migration Across Banking Applications**.

```
Repository → Discovery → Risk → Migration Plan → Candidate Patch → Verification → Human Approval → Controlled Migration
```

**AI proposes. Verification validates. Humans approve.**

---

## Quick start

Requirements: **Node.js 20.10+** and **Python 3.9+** on `PATH` (as `python3`, `python` or `py`, or set `CRYPTOSHIFT_PYTHON`).
Python is used to run the sample repository's real tests and tools. Without it, the app still runs, but build, test,
conformance and protocol checks report **unavailable** — never passed.

```bash
npm run setup     # installs frontend dependencies (the backend has none)
npm run dev       # API on http://localhost:8787 + UI on http://localhost:5173
```

Open http://localhost:5173. Then:

1. **First run:** the terminal running the API prints a one-time **setup code** (also saved to
   `backend/data/setup-token`). Enter it in the browser with a username and a password of 15+ characters to
   create the first administrator.
2. **Settings → Team accounts:** add at least one **engineer** and two **reviewers**. The four-eyes rule means
   the person who runs verification cannot approve the same patch.
3. As an engineer: **Verification Center** → pick a patch → **Run verification** (real checks, a few seconds).
4. As a different reviewer: approve a *verified candidate*, release it, and roll it back from **Rollback & Recovery**.
5. **Reports & Audit:** check the audit log's integrity, export the inventory as a CycloneDX 1.6 CBOM, and
   download the full report.

| Role | Can |
|---|---|
| Viewer | Read findings, plans, verification results and the audit log |
| Engineer | Viewer rights, plus scan, propose and run verification (and the optional AI review) |
| Reviewer | Engineer rights, plus approve, reject, release and roll back |
| Administrator | Reviewer rights, plus manage accounts and reset demo state |

Production-style: `npm start` builds the UI and serves it from the API on http://localhost:8787 (bound to
127.0.0.1; set `HOST=0.0.0.0` to expose it, behind a TLS proxy with `CRYPTOSHIFT_SECURE_COOKIE=1`).
Container: `docker build -f docker/Dockerfile.web -t cryptoshift-web .` from the repository root, then
`docker run -p 127.0.0.1:8787:8787 -v cryptoshift-data:/data --read-only --tmpfs /tmp cryptoshift-web`.

To start over: **Settings → Reset demo state** (accounts and the audit log are kept), or delete `backend/data/`
to remove everything, including accounts.

| Environment variable | Purpose |
|---|---|
| `PORT`, `HOST` | Listen address (default `127.0.0.1:8787`) |
| `CRYPTOSHIFT_DATA_DIR` | Where state, accounts, the audit log and working copies live (default `backend/data`) |
| `CRYPTOSHIFT_SETUP_TOKEN` | Fixed setup code for hosted deployments (16+ characters; delete it after setup) |
| `CRYPTOSHIFT_SECURE_COOKIE=1` | Mark cookies `Secure` and send HSTS (set when served over HTTPS) |
| `CRYPTOSHIFT_PYTHON` | Python used to run verification checks |
| `CRYPTOSHIFT_MAX_RUNS` | Parallel verification runs (default 2) |
| `SARVAM_API_KEY` | Optional AI review of candidate patches (advisory only) |

Security model, threat table and known limitations: [SECURITY.md](SECURITY.md).

## Testing

```bash
npm test          # unit tests + 37 end-to-end checks (own API on port 18787, temporary data directory)
npm run typecheck # strict TypeScript, no unused locals
```

`npm test` proves, against a fresh state:
- **Behaviour:** every finding's file and line match the real source; undeclared fields stay unknown; the
  inferred `auth ↔ payments` cycle is reported; the declared-only plan respects every edge.
- **The gate:** unverified and failed patches cannot be approved; verify → approve → release → rollback restores
  the original file byte for byte.
- **Security:** sessions are required; roles are enforced; CSRF and cross-site simple requests are refused;
  sign-in is throttled; decisions carry the signed-in identity, never a client-supplied name; the four-eyes
  rule holds; malformed URLs, path traversal and oversized bodies are refused without crashing; the audit
  chain verifies, and detects an on-disk edit after restart.
- **Standards:** findings carry NIST IR 8547 deadlines; the CBOM is CycloneDX 1.6.

The UI was checked in a browser at 1024 px and 375 px. All 17 routes have no horizontal scroll, and axe-core
reports 0 WCAG 2.2 A/AA violations on every route and on the sign-in screen.

The UI was additionally tested with Playwright (desktop 1440 px and phone 390 px, reduced motion): all 13 routes load
with no console errors; all four figures are keyboard-operable (arrows, Home/End, Escape) and pointer-selectable; the
callout and readout always match the selected component; there is no horizontal scroll on phones; the backend-offline
state is explicit.

## What is real and what is not

| Area | How it works | Honest limits |
|---|---|---|
| Repository | `sample-repos/northbank-core`: a small Python banking monorepo bundled for the demo, copied to `backend/data/workspaces/` | One sample repo. Add others by placing a folder with a `cryptoshift.services.json` in `sample-repos/`. |
| Discovery | Line-by-line rule scanner (`backend/src/scanner.js`) records file, line, column, snippet and references | Rules target this repo's crypto-provider API. Real codebases need rules for their libraries (JCA, OpenSSL, `cryptography`, …). |
| Role / context | From the manifest when declared, otherwise inferred from identifiers and references, otherwise **unknown** | Inferred values are labelled as such everywhere. |
| Risk | Transparent additive score; every factor is shown; missing evidence scored conservatively and flagged | A prioritisation heuristic, not a measure of exploitability. |
| Dependencies | Declared edges (manifest) + import-inferred edges; Tarjan SCC for cycles; Kahn layering for waves | Runtime-only calls are not visible to static analysis. |
| Candidate patches | Deterministic rule engine, labelled `rule-engine/1.0 (no LLM configured)` | An optional AI reviewer (Sarvam, needs `SARVAM_API_KEY`) can comment on a candidate; its output is advisory and never unlocks approval. |
| Diff, build, tests | Executed in throwaway baseline and candidate copies (`compileall`, `unittest`) | The sample's crypto provider is a stub that records parameter sets; it performs no real cryptography. |
| Crypto conformance | Compares declared ML-KEM / ML-DSA sizes with FIPS 203 / 204 tables | **Not** a known-answer test. |
| Protocol traces | `tools/negotiate.py` models each peer's handshake before and after the patch | A capability model, not packet captures of live traffic. |
| Approval / release / rollback | Server-enforced gate on the signed-in reviewer's role; four-eyes; release writes the working copy and stores a checkpoint; rollback refuses if the file changed since | Local accounts only (no SSO or MFA yet; see SECURITY.md). |
| Audit log | Append-only, HMAC-chained; integrity check and chain head shown on Reports & Audit | Detects edits, not silent truncation of the newest entries unless you keep a copy of the chain head. |
| NIST deadlines | Each finding shows NIST IR 8547's transition dates (deprecated after 2030, disallowed after 2035) | Dates follow NIST; your regulator's timeline may differ. |
| CBOM export | CycloneDX 1.6 `cryptographic-asset` components with file/line evidence | Covers the algorithms the scanner detects. |

"Verified candidate" means every configured required check passed. It is evidence for human review, not a proof of
absolute security.

## The Anatomy Lab

| Route | Figure | Data source |
|---|---|---|
| `/anatomy` | Index with live previews drawn by the same components as the detail pages | All of the below |
| `/anatomy/quantum-computer` | Dilution-refrigerator cutaway of one superconducting-qubit platform | Labelled educational model |
| `/anatomy/cryptographic-asset` | Evidence cabinet: ten drawers, one per field of a finding; pips show declared / inferred / unknown; a dial reads the risk score | A real scanner finding |
| `/anatomy/banking-dependencies` | Backplane bench: modules in migration-wave lanes, conduits for dependencies, a fenced holding bay for blocked services; synced 2-D graph | Backend graph and plan |
| `/anatomy/verified-migration` | Inspection line: the candidate rides a carriage that stops at the first check it cannot clear, before a key-switch approval gate and a release barrier | Latest real verification run, decisions and checkpoints |

Every figure shares one frame (`frontend/src/anatomy/AnatomyFrame.tsx`): the Anatomy card, selection by pointer,
keyboard and a component list (the text alternative), an HTML callout pinned to the selected part (hidden on phones in
favour of the detail panel), a live readout, a guided tour, reduced-motion support and a render fallback.

### Anatomy kit integration

`frontend/src/anatomy/kit/` contains `iso-kit.ts`, `iso.css`, `react/draw.tsx` and `react/live.tsx` from
[wheresryan22/anatomy](https://github.com/wheresryan22/anatomy) (MIT), unmodified apart from an attribution header.
Reusable parts built on it are in `frontend/src/anatomy/parts.tsx`; each figure keeps a model, static geometry and a
live component separate, following the skill's React guidance.

Deliberate deviations from the reference kit, documented here as required:

- **No geometry audit (`kit/audit.mjs`) or line-end check (`scripts/lines.mjs`).** The figures use no lathe or tube
  parts; painter's order is set by construction and verified by inspecting screenshots at desktop, phone and zoom.
  The quantum cutaway's coaxial lines pass through the plates (implied feedthrough holes are not drawn).
- **No WebGL layers.** Nothing in these subjects (no fire, water or lamp light) needs a shader.
- **Dimming by faded edges, not opacity.** Lowering opacity on overlapping solids made them see-through, so unselected
  parts keep opaque fills and only their lines fade.
- **Selection colour.** The kit is monochrome with one lit accent; status colours (green / red / amber) appear only where
  status *is* the subject: lamps, pips and the selection accent.

## Project layout

```
backend/src/        server.js (routes, RBAC, CSRF, headers) · auth.js · auditlog.js · standards.js (NIST deadlines, CBOM)
                    scanner.js · graph.js · patches.js · verify.js · store.js · repos.js
backend/data/       created at runtime: state.json, users.json, audit.log + audit.key, working copies
frontend/src/       api/ · components/ (Shell, ui, FileViewer, ReviewActions, TraceCompare) · pages/ · figures/ · anatomy/
sample-repos/       northbank-core: the bundled sample banking repository
frontend/src/auth/  sign-in, first-run setup, session and role context
tests/              unit.test.mjs · api.test.mjs
```

## API

Public: `GET /api/health` · `GET /api/auth/status` · `POST /api/auth/setup` · `POST /api/auth/login`.
Signed in: `GET /api/auth/session` · `POST /api/auth/logout` · `POST /api/auth/password` · `GET /api/system` ·
`GET /api/audit?limit&offset` · `GET /api/audit/verify` · `GET /api/repositories/:id/cbom` · `GET /api/users` (admin) ·
`POST /api/users` (admin) · `POST /api/users/:id` (admin) · `GET /api/repositories` · `POST /api/repositories/:id/scan` · `POST /api/repositories/:id/reset` ·
`GET /api/repositories/:id/findings` · `GET /api/findings/:id` · `GET /api/repositories/:id/file?path=` ·
`GET /api/repositories/:id/graph` · `GET /api/repositories/:id/plan?inferred=0|1` · `GET /api/repositories/:id/patches` ·
`POST /api/findings/:id/propose` · `GET /api/patches/:id` · `POST /api/patches/:id/verify` · `GET /api/runs/:id` ·
`POST /api/patches/:id/decision` · `POST /api/patches/:id/release` · `GET /api/repositories/:id/checkpoints` ·
`POST /api/checkpoints/:id/rollback` · `GET /api/repositories/:id/traces` · `GET /api/audit` · `POST /api/admin/reset-state`
