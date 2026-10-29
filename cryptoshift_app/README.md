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

1. **Settings** → enter a reviewer name (recorded on every decision).
2. **Verification Center** → pick a patch → **Run verification** (real checks, a few seconds).
3. Approve a *verified candidate*, release it, and roll it back from **Rollback & Recovery**.
4. Explore the four figures in **Anatomy Lab**.

Production-style: `npm start` builds the UI and serves it from the API on http://localhost:8787.

To start over: **Settings → Reset demo state**, or delete `backend/data/`.

## Testing

```bash
npm test          # backend integration test (starts its own API on port 18787, restores your data afterwards)
npm run typecheck # strict TypeScript, no unused locals
```

`npm test` proves, against a fresh state: every finding's file and line match the real source; undeclared fields stay
unknown; the inferred `auth ↔ payments` cycle is reported; the declared-only plan respects every edge; unverified and
failed patches cannot be approved; approval needs a named reviewer; and verify → approve → release → rollback restores
the original file byte for byte.

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
| Candidate patches | Deterministic rule engine, labelled `rule-engine/1.0 (no LLM configured)` | No language model is wired in. A model-backed proposer would plug into the same gate. |
| Diff, build, tests | Executed in throwaway baseline and candidate copies (`compileall`, `unittest`) | The sample's crypto provider is a stub that records parameter sets; it performs no real cryptography. |
| Crypto conformance | Compares declared ML-KEM / ML-DSA sizes with FIPS 203 / 204 tables | **Not** a known-answer test. |
| Protocol traces | `tools/negotiate.py` models each peer's handshake before and after the patch | A capability model, not packet captures of live traffic. |
| Approval / release / rollback | Server-enforced gate; release writes the working copy and stores a checkpoint; rollback refuses if the file changed since | No authentication: the reviewer name is self-declared. |

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
backend/src/        server.js (routes) · scanner.js · graph.js · patches.js · verify.js · store.js · repos.js
backend/data/       created at runtime: state.json + working copies (safe to delete)
frontend/src/       api/ · components/ (Shell, ui, FileViewer, ReviewActions, TraceCompare) · pages/ · figures/ · anatomy/
sample-repos/       northbank-core: the bundled sample banking repository
tests/              api.test.mjs
```

## API

`GET /api/health` · `GET /api/repositories` · `POST /api/repositories/:id/scan` · `POST /api/repositories/:id/reset` ·
`GET /api/repositories/:id/findings` · `GET /api/findings/:id` · `GET /api/repositories/:id/file?path=` ·
`GET /api/repositories/:id/graph` · `GET /api/repositories/:id/plan?inferred=0|1` · `GET /api/repositories/:id/patches` ·
`POST /api/findings/:id/propose` · `GET /api/patches/:id` · `POST /api/patches/:id/verify` · `GET /api/runs/:id` ·
`POST /api/patches/:id/decision` · `POST /api/patches/:id/release` · `GET /api/repositories/:id/checkpoints` ·
`POST /api/checkpoints/:id/rollback` · `GET /api/repositories/:id/traces` · `GET /api/audit` · `POST /api/admin/reset-state`
