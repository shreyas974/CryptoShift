# CryptoShift web app: user audit and fix report

Date: 2026-10-30 · Branch `feature/webapp-v2` · Scope chosen by the owner: **audit and fix the existing app**. Pages
that do not exist (Repository Management as its own page, AI Patch Studio, Protocol Traces as its own page, a
four-figure Anatomy Lab) were **not built**; they are listed as gaps in section E.

Method: signed in as a first-time user (local `demo` approver, and the isolated E2E accounts), walked every route
in system Chrome at 1440, 1024 and 390 px, recorded console errors, failed requests and page width, read every
screenshot, then fixed, added a test, and re-ran. Every number below was observed in this session.

## A. User perspective

- **Ten-second test:** passes. The hero says "Find, plan and verify your post-quantum migration", and a new
  workflow strip (Overview) lists the ten steps from repository to report, each with an honest status badge and a
  link to where it happens.
- **Could a first-time user finish the journey alone?** After the fixes, yes. Before them they got stuck at three
  points:
  1. There was no way to try the tool without preparing an upload.
  2. The risk score was a raw formula string (`crypto_exposure=3.00×3=9.00; ...`).
  3. Unevaluated gates showed `? UNKNOWN`, which reads as a defect.
- **Remaining confusion:** "Candidate" is a text recommendation, not a code patch. This is now said on the Overview
  workflow strip, but a user expecting a diff will still look for one. Jargon such as `purpose_resolved` (a gate
  name) is shown raw in the gate matrix header.

## B. Critical problems found and fixed

| # | Issue | Page | Reproduce | Root cause | Fix | Test |
|---|---|---|---|---|---|---|
| 1 | No way to scan without uploading; the "register/select a repository" step was missing | Datasets & runs | open Pipelines → Datasets & runs as a new analyst | only upload existed; the allow-listed repos had no UI | "New here? Start with a demo repository" card: two built-in SYNTHETIC repos, one click runs discovery + plan (`GET /api/v1/demo-repos`, `POST /api/v1/runs/demo`, path-safe, audited) | pytest `test_demo_repository_run_needs_no_upload`; E2E acceptance journey |
| 2 | Risk score unexplained | Migration plan | open Plan: Reason column shows a formula string | API passed the planner's debug string through | API returns `risk_factors` (meaning, input, weight, points, unknown flag) from the planner's real weights; each row expands into a factor table whose points add up to the score; "Missing information" column; "unknown is scored in the middle, not as low risk" | pytest `test_findings_state_role_certainty_and_risk_is_explained` (sum check, unknown flag); E2E |
| 3 | Gates never evaluated shown as `? UNKNOWN` | Verification | gate matrix, ledger_audit row | gate code runs only gates a step's purposes need; UI filled gaps with UNKNOWN | **NOT RUN** (purpose unresolved) / **NOT APPLICABLE** (not required) with legend; both added to the status vocabulary (front and back) and never count as pass | Vitest `audit.test.tsx` (3 tests); E2E asserts 0 "UNKNOWN" in the matrix |
| 4 | A finding's role certainty not stated | Inventory | open a HOLD finding | no field separated literal evidence from inference | `role_certainty` per finding: algorithm **CONFIRMED** (literal value in file; INFERRED if detector confidence is low), role **INFERRED** or **UNKNOWN / MANUAL REVIEW**; detail rewritten as What / Where / Evidence / Algorithm / Role / Why / Why migrate / Candidate / Service / Next step | pytest (HOLD rows are always UNKNOWN); Vitest; E2E |
| 5 | Clicking a finding row seemed to do nothing | Inventory | click a row near the top | detail card rendered below the fold | detail moved first and scrolled into view (offset for the sticky bar) | E2E (detail visible after click) |
| 6 | Approvals appeared in the feed as "e2e-approver approve" | Activity / bell | approve a step, open Activity | wording map keyed `approval`; the audit action is `approve` | key fixed | pytest `test_every_audited_action_has_plain_words_in_the_activity_feed` (AST check of every `audit(...)` call); E2E |
| 7 | Plan export only reachable from the command palette | Migration plan | look for "export" on Plan | no button | Markdown and JSON download buttons on the Tasks card | pytest `test_exports_are_valid_files` (JSON parses, embedded JSON in Markdown parses); E2E downloads and parses the JSON |
| 8 | Refresh lost the open run | Datasets & runs | open a run, press F5 | selection kept only in React state | `#/runs?run=<id>` via `history.replaceState` | E2E reloads and finds the same run |
| 9 | (earlier, v2.1) phone page up to 751 px wide; menus see-through in light theme; borderless controls in light theme | all | 390 px; light theme | `.badge` display beat Tailwind `hidden`; wide tables; white edge token | wrappers, in-card table scroll, opaque menu, ink borders | crawl: page width = viewport on all 16 routes at 1440/1024/390 |

## C. Route-by-route audit (after fixes)

Automated crawl, all 16 routes × 1440/1024/390: **0 runtime errors, 0 failed requests** (the only console error is
the expected 401 from `/auth/me` before sign-in), **0 pages wider than the viewport**, reload keeps the route.

| Route | Status | Notes / fixes |
|---|---|---|
| Overview | OK | hero, new workflow strip, pillars, pipeline stages, Fig. 1, KPIs, activity, BYOD band. Fig. 1 is decorative, labelled as such |
| Data & evidence | OK | file, producer, SHA-256, regenerate command per report |
| Activity | OK (fixed #6) | |
| Inventory | OK (fixed #4, #5) | HOLD filter; certainty badges; escaped snippets |
| Dependencies | OK | OBSERVED solid / DECLARED dashed / INFERRED dotted + text edge list with file:line; conflicts listed |
| Detection evaluation | OK | separate sets; held-out recall 0.1161 shown with "AI-draft labels" |
| Migration plan | OK (fixed #2, #7) | waves agree with the Tasks table; infeasible schedules on uploads are shown as such |
| Verification | OK (fixed #3) | compatibility matrix with negative cases; before/after traces; overhead labelled loopback |
| Approval & rollback | OK | approve disabled until READY + name + hash prefix + acknowledgement; rollback restore/trigger/recovery check; "never restore SHA-1/3DES" warning |
| Datasets & runs | OK (fixed #1, #8) | upload, demo repos, stage stepper, results tabs, downloads |
| Reports | OK | print to PDF; shows audit-chain validity and approval counts |
| Claims & limits | OK | |
| ML & AI | OK | assistant mode badge; TEMPLATE_FALLBACK when Member 3's service is down |
| Audit log | OK | verify chain |
| Users & roles | OK | last-approver and self-demotion rules |
| Settings | OK | |

Accessibility: axe (WCAG 2.0/2.1/2.2 A+AA) **0 violations on 16 routes × 2 themes**, now asserted by the E2E suite;
token contrast test (Vitest) passes including the new accent. Keyboard: the menus, the palette (Ctrl K), table rows
(Enter) and Fig. 1 (arrow keys) work. Text over the moving canvas still needs a human check ("incomplete" in axe).

## D. Technical validation (observed)

| Check | Result |
|---|---|
| Frontend build (`npm run build`) | OK; main chunk ≈ 0.5 MB (≈ 150 kB gzip), Tier 2 pages code-split |
| `npx tsc -b --noEmit` / `npx eslint . --max-warnings 0` / Prettier | 0 / 0 / clean |
| Frontend tests (`npx vitest run`) | **34 passed** |
| Backend API tests (`pytest tests/test_webapp_api.py`) | **24 passed, 1 skipped** (symlink creation not permitted on this Windows account) |
| Existing suites (`python -m unittest discover -s tests`) | **100 OK, 1 skipped** |
| `ruff` (API, run script, tests) | clean |
| Browser tests (`npx playwright test`, installed Chrome) | **10 passed** |
| Responsive (1440 / 1024 / 390) | page width = viewport on every route |
| Exports | plan JSON downloaded in the browser and parsed; plan JSON and verification Markdown parsed in pytest; run outputs downloadable (E2E) |
| End-to-end journey (section 11 of the brief) | see below |
| `npm audit` / `verify_repo` / key-pattern scan of `web/dist` | 0 / PASS / 0 |

Final acceptance journey (E2E test "first-time user journey", isolated server on 127.0.0.1:8611 with temp DB and
temp approvals store):

| Step | Result |
|---|---|
| 1–2 launch, Overview, workflow strip visible | PASS |
| 3–4 select a demo repository and scan it | PASS (run succeeded; discovery + plan) |
| 5–7 open a HOLD finding: file:line evidence, role UNKNOWN / MANUAL REVIEW, next step | PASS |
| 8 risk explanation (factors add up) | PASS |
| 9 dependency-aware plan, export downloaded and parsed | PASS |
| 10 review a candidate patch | **NOT AVAILABLE**: candidates are text recommendations; no patch generator exists |
| 11–12 verification results: gates never UNKNOWN; NOT APPLICABLE shown | PASS (gates come from the saved loopback evidence; the lab was not re-run in this test) |
| 13 before/after protocol traces | PASS (Verification page; TEST SCENARIO label) |
| 14 rollback plan | PASS (Approval & rollback page) |
| 15 record a human approval (test environment only) | PASS: one READY step approved; row shows APPROVED |
| 16 report reflects it; audit chain valid | PASS |
| 17 refresh keeps state (open run) | PASS |
| 18 navigate back through routes | PASS (crawl + reload checks) |

## E. Remaining limitations

- **Not built:** a candidate-patch generator with diffs ("AI Patch Studio"); Repository Management as its own page;
  a separate Protocol Traces page (traces live on Verification); the four-figure Anatomy Lab (only Fig. 1 exists).
- **"Full" pipeline:** re-runs the OpenSSL 3.5 loopback lab from the UI but was not run in this audit.
- **Member 3 scheduler limit:** more than 15 services fails the plan stage with "Exhaustive baseline too large". Loose
  files without folders can inflate the service count.
- **Data credibility:**
  - Gates use generic loopback evidence. READY means eligible for human review, not verified on the service's stack.
  - The risk weights are hand-set.
  - Held-out recall is 0.116 with AI-drafted labels.
- **Hosting:** not deployed. Vercel was assessed and declined for now: its functions don't keep files between
  requests and stop background work.
- **Accessibility:** human review of text over the animated canvas is still needed.
- **Licences:** lightningcss (MPL-2.0) and caniuse-lite (CC-BY-4.0) are dev-only. They need an owner decision.

## F. Final assessment (1–10, with evidence)

| Category | Score | Evidence |
|---|---|---|
| First-time usability | 7 | workflow strip, demo-repo one-click run, plain finding detail; jargon gate names remain |
| Workflow clarity | 7 | 10-step strip with honest statuses; the candidate-patch step is text-only |
| Visual consistency | 8 | one token set, shared components; screenshots in both themes |
| Frontend functionality | 8 | 10 E2E journeys pass; every visible control on audited paths works |
| Backend integration | 8 | 24 API tests; all pages read real reports; uploads and demo runs execute the real pipelines |
| Error handling | 7 | actionable refusals (traversal, sensitive files, size, role, rate limit); missing files say how to produce them |
| Data credibility | 8 | no fabricated numbers; NOT RUN / NOT APPLICABLE; unknown ≠ low risk; SIMULATOR and TEST SCENARIO labels |
| Accessibility | 8 | axe 0 on 32 combinations; keyboard paths; human review still pending |
| Responsive behaviour | 8 | no horizontal scroll at 1440/1024/390 |
| PQC-01 requirement coverage | 6 | discovery, inventory, plan, verification, approval, rollback, report covered; patch generation missing |

## G. Launch instructions

```powershell
# install (repo .venv and web/ only)
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-member3.txt -r requirements-api.txt
cd web; npm ci; npm run build; cd ..
# database: created and migrated automatically (Alembic) on first start; then create the first account
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m cryptoshift.api.admin create-user <name> approver
# run (single process, 127.0.0.1:8600)
powershell -ExecutionPolicy Bypass -File scripts\run_full_demo.ps1 start
# development: backend on 8600 + Vite dev server on 5173
.\.venv\Scripts\python.exe -m uvicorn --factory cryptoshift.api.main:app_factory --host 127.0.0.1 --port 8600
cd web; npm run dev
# tests
.\.venv\Scripts\python.exe -m pytest tests/test_webapp_api.py -q
.\.venv\Scripts\python.exe -m unittest discover -s tests
cd web; npx tsc -b --noEmit; npx eslint . --max-warnings 0; npx vitest run; npx playwright test
```
