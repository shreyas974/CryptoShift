# Web app v2 handoff

## What is built (status labels per `docs/stage0/claims-register.md`)

| Area | Status | Evidence |
|---|---|---|
| Backend API v1: 37 paths; read adapters with schema checks; sessions, roles, CSRF, rate limits, CSP and security headers; hash-chained append-only audit; allow-listed jobs; scan path safety; assistant proxy with in-process fallback; exports | VERIFIED | pytest 20 passed, 1 skipped (symlink case not runnable on this Windows account); ruff clean |
| Frontend: 12 pages, glass design system, procedural background, evidence drawer, command palette, approval dialog, themes and accessibility modes, code-split Tier 2 | VERIFIED | tsc strict, ESLint, Prettier clean; Vitest 30; Playwright 9 in the installed Chrome |
| Fig. 1 "Sorting line" (anatomy skill): isometric, data-driven, keyboard + pointer, reduced motion | VERIFIED (decorative explanation, not evidence) | Vitest figure tests; E2E figure test; screenshots reviewed in both themes |
| Accessibility | VERIFIED for automated rules | axe (WCAG 2.0/2.1/2.2 A+AA tags): 0 violations on 16 pages x 2 themes (now asserted by the E2E suite); automated token contrast test (min 6.50:1); "incomplete" items (text over the blurred canvas) need human review |
| Performance | measured on this machine only | Chrome 156, 1440x900, i5-11400H: inventory ready 49 ms, DOMContentLoaded 93 ms, rAF 144 fps (display cap) |
| Security checks | VERIFIED | listens on 127.0.0.1 only; CSP has no unsafe-inline (one sha256 hash for Cytoscape's fixed container rule); 0 provider-key names or key-shaped strings in bundle, logs or outputs; `npm audit` 0; `pip-audit` 0 known; `verify_repo` PASS |
| v2.1 redesign (top bar + drop-down menus, sphere hero, three-up cards, news lists, gradient footer; own assets only) | VERIFIED | screenshots in both themes and at 390 px (no horizontal scroll); axe 0 on 16 pages × 2 themes |
| Dataset upload → pipeline run (discovery / plan / full) with outputs | VERIFIED (discovery, plan); full = PLANNED-untested in UI | pytest zip safety + end-to-end run; E2E upload; manual zip run on the fixture gave 45 findings, 10 steps (3 READY), same as the CLI |
| Users & roles, activity feed, printable report | VERIFIED | pytest (last-approver and self-demotion rules, disabled login refused, audit chain valid); E2E |
| Allow-listed folder scan UI | PARTIAL | API only |
| Docker, GitHub Actions CI, visual regression, PDF export, i18n | PLANNED | Docker not installed; CI needs owner approval |

## Waiting on Members 2 and 3

- Member 3: the assistant service (`scripts/run_agent.ps1`) needs `scratch/derived/member3/bundle/plan.json` in this checkout to run beside the app. Without it, the app uses the in-process template fallback (by design).
- Member 2 / Member 1: human review of the AI-drafted labels (`data/labels/public_code/review_sheet.csv`) before any detection number is presented as more than a draft.

## Known gaps and owner decisions

- **Licences:** lightningcss (MPL-2.0) and caniuse-lite (CC-BY-4.0) are build-time-only tools, not in the bundle, and outside the accepted list. Owner decision needed (THIRD_PARTY_NOTICES.md).
- **TypeScript:** `noUncheckedIndexedAccess` was turned off so the vendored anatomy kit compiles unmodified; `strict` stays on.
- **Vendored kit:** `web/src/components/iso/` is excluded from ESLint and kept byte-identical to upstream (commit 1482e84).
- **Anatomy checks:** the skill's own `audit` / `lines.mjs` checks target standalone builds with pipes and cables. They were not run on this React figure; it was verified with tests and screenshot review.
- **Test server:** the E2E backend raises the login rate limit (test server only); production stays 5/min.
- **Scheduler size limit:** uploads with more than 15 services make the Member 3 plan stage fail ("Exhaustive baseline too large"); loose files without folders can inflate the service count. Shown honestly as FAIL.
- **Design reference:** the v2.1 look follows the owner's reference site's style only; no logo, image, text or layout file was copied.
- **Sign-out bug:** found by E2E (the session ended but the UI stayed signed in) and fixed by resetting the session query.
