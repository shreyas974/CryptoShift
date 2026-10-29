# Member 4 UI design: CryptoShift demo console (for approval; no UI code yet)

**Goal.** A calm, honest security dashboard that shows only real outputs from Members 2 and 3, and says plainly what
is VERIFIED, SIMULATED, SYNTHETIC, PLANNED or BLOCKED. It must be readable on a projector in a 5-minute judge demo.

**Stack.**
- Streamlit multi-page app (`streamlit` is already a dependency; no JavaScript build), in `src/cryptoshift/ui/`.
- Started by `scripts\run_ui.ps1` and bound to **127.0.0.1** only.
- The existing `src/cryptoshift/ui/app.py` (Member 4's earlier MVP-slice view) stays untouched. The new app lives in `src/cryptoshift/ui/console/`.

## 1. Data layer (one adapter, no page reads files directly)

`ui/console/data.py` returns a `Loaded(value, source)` object. The `source` carries the file, its modified time, the producer, the status label and a schema check result.

| Key | File (default; folder overridable with `CRYPTOSHIFT_UI_DATA_DIR`) | Schema |
|---|---|---|
| plan | `reports/member3/plan.json` | `schemas/member3/plan.schema.json` |
| gates | `plan.steps` | `schemas/member3/gate_results.schema.json` |
| rollback | `plan.rollback` | `schemas/member3/rollback_record.schema.json` |
| inventory | `scratch/derived/inventory-v11/<target>/inventory.cbom-like.json` | `schemas/inventory-cbom-like-1.1.schema.json` |
| relationships | `.../relationships.json` | `schemas/relationships.schema.json` |
| verification evidence | `scratch/derived/member3/verification_evidence.json` | – (key checks) |
| scheduling comparison | `scratch/derived/member3/scheduling_comparison.json` | – |
| ML A / B | `scratch/derived/member3/ml_cesnet.json`, `ml_purpose_triage.json` | – |
| assistant eval | `scratch/derived/member3/agent_eval.json`, `agent_eval_sarvam.json`, `scratch/derived/agent_usage.json` | – |
| detection eval | `scratch/derived/public-label-eval/eval_{calibration,calibration-2,held_out}.json`, `scratch/derived/cryptoapi-bench/cryptoapi_bench_eval.json` | – |
| datasets | `data/registry.json`, `data/real/dataset_manifest.json` | – |
| claims | `docs/stage0/claims-register.md` (rendered read-only) | – |

**Rules:**
- **A file is missing:** show a "file missing" card with the command that produces it. The app never crashes.
- **Schema mismatch:** show a "schema mismatch" card listing the first 3 errors.
- **Unknown status values** render as `UNKNOWN`, never as passed.
- **SAMPLE fixtures** (`ui/console/sample/`, bannered **SAMPLE DATA, SYNTHETIC**) are used only where a real file truly does not exist, and the banner says which file.
- **Demo mode:** reads a frozen snapshot folder (`scratch/derived/ui-snapshot/<date>/`) produced by a snapshot command. A grey banner shows "Offline demo snapshot from <time>".

## 2. Visual language

| Token | Light | Dark | Use |
|---|---|---|---|
| background | `#f7f8fa` | `#111418` | page |
| surface | `#ffffff` | `#1b2027` | cards |
| text | `#1c2430` | `#e6e9ee` | body (contrast ≥ 7:1) |
| muted | `#5b6573` | `#9aa4b2` | captions (≥ 4.5:1) |
| **accent (one)** | `#1f6feb` | `#58a6ff` | links, selected nav, primary button |

**Badges.** These are the only colours besides the accent. Each badge is **text + icon** and never relies on colour alone:

| Badge | Icon | Colour family |
|---|---|---|
| VERIFIED | ✔ | green |
| PARTIAL | ◐ | amber |
| MOCKED | ⚠ | grey |
| SIMULATED | ⚛ | violet |
| SYNTHETIC | 🧪 | grey |
| PLANNED | ⏳ | blue-grey |
| BLOCKED | ⛔ | red |
| UNKNOWN | ? | grey |

| Badge | Icon | Meaning |
|---|---|---|
| OBSERVED | 👁 | edge evidence in a file, with line |
| DECLARED | 📄 | descriptor only |
| INFERRED | ↯ | assumption, with reason |
| confidence high / med / low | ●●● / ●●○ / ●○○ | |
| ambiguity | "ambiguous" / "purpose unknown → HOLD" | text tag |

**Typography and layout:**
- System sans; base 16 px, tables 15 px, page titles 28 px.
- At most 2 columns at 1280×720; 3 columns at 1920×1080. Tables use `st.dataframe` with fixed column widths and no clipped cells.

**States:**
- *loading:* spinner + "reading <file>";
- *empty:* "No findings for this filter";
- *error:* a red card with the file and reason. No raw tracebacks are shown.

**Accessibility:**
- All controls are reachable by keyboard (native Streamlit widgets).
- Every chart has a text-equivalent table under an expander labelled "Data behind this chart".
- The dependency graph has a text edge list.
- No information is carried by colour alone.

**Safety in rendering:**
- All scanned text (snippets, file names, evidence) goes through one `escaped_text()` helper and is rendered as plain text (`st.text` / `st.code`). It is never rendered with `unsafe_allow_html`.
- Snippets are capped at 160 characters on display.

Every page ends with a **source-and-status footer**: `file · modified time · producer · label`.

## 3. Pages (10) and wireframes

```
┌ sidebar ───────────────┐┌───────────────────────────────────────────────────────────────┐
│ CryptoShift            ││ HONESTY BANNER: Prototype for a hackathon demo. Synthetic bank,│
│ ● 1 Overview           ││ loopback TLS test scenario. Not production, not certified.     │
│ ○ 2 Data & evidence    │├───────────────────────────────────────────────────────────────┤
│ ○ 3 Inventory          ││  page content                                                  │
│ ○ 4 Dependencies       ││                                                                │
│ ○ 5 Migration plan     ││                                                                │
│ ○ 6 Verification       ││                                                                │
│ ○ 7 Approval & rollback││                                                                │
│ ○ 8 Detection eval     ││                                                                │
│ ○ 9 ML & AI            ││                                                                │
│ ○ 10 Claims & limits   ││                                                                │
│ ─────────────          │├───────────────────────────────────────────────────────────────┤
│ Data: LIVE ▸ / DEMO    ││ footer: source file · time · producer · label                  │
│ Theme: light/dark      │└───────────────────────────────────────────────────────────────┘
│ Cloud AI: OFF ⛔        │
└────────────────────────┘
```

| # | Page | Content (all from the adapter) | Must show honestly |
|---|---|---|---|
| 1 | **Overview** | Pipeline strip with one badge per stage. Stages and current status: Inventory (VERIFIED), Graph (VERIFIED), Risk (PROVISIONAL), Schedule (VERIFIED; Opt equal), Gates (3 READY / 3 PROPOSED), Approval (none), Rollback (rehearsed), Assistant (mode). Plus 4 KPI tiles: findings, services, steps READY, plan hash (short). | Honesty banner; "READY = generic loopback evidence, not service verification" |
| 2 | **Data & evidence sources** | Table of datasets (registry) with type badge (REAL public / SYNTHETIC / benchmark) and licence; public repos with commit and licence; CESNET "not PQC labels" note | Data is read-only; datasets are never relabelled |
| 3 | **Inventory** | Filters (service, purpose, family, detector, confidence, "only HOLD"). Findings table: ID, `file:line`, service (+ attribution basis tooltip text), family, purpose, ambiguity, candidate. Selecting a row shows the escaped snippet and rationale. Side cards: by purpose, by detector. | Candidate is "for human review"; unknown purpose → HOLD; CBOM-like (CycloneDX subset only when validated) |
| 4 | **Dependencies** | Graph (networkx layout → matplotlib/Plotly static image). Edge style: OBSERVED solid, DECLARED dashed, INFERRED dotted, with a text legend. Unknown endpoints and unattributed findings in red-bordered lists. Text edge list with file:line. | Cycles and conflicts listed, never hidden |
| 5 | **Migration plan** | Waves Gantt-style chart + table (task, wave, risk + reason, finding IDs). Side-by-side cards: Baseline · QpiAI Opt (local solve) · QCloud simulator QAOA, each with objective/runtime/status. | "Equal, not better"; QAOA = SIMULATOR, P(opt) vs uniform; risk score "provisional, not validated" |
| 6 | **Verification** | Gate matrix (step × gate, text + icon). Compatibility matrix incl. NEGATIVE cases (expected vs observed). BEFORE/AFTER traces (group, cipher, bytes, command lines). Overhead (median, p95, bytes, environment). | "TEST SCENARIO, loopback, test keys"; loopback timing ≠ network; ML-KEM self-test ≠ NIST KAT |
| 7 | **Approval & rollback** | Per step: state, blocking gates. **Approve** control enabled only when every required gate passes; needs a typed approver name and the typed plan hash (first 12 characters); calls Member 3's `approval` function; no "approve all". Rollback record: what to restore, snapshot hash, trigger, recovery check, rehearsal result, SHA-1/3DES warning. | You (human) approve; tests use the fake approver "TEST-ONLY" in a temp store |
| 8 | **Detection evaluation** | Separate tables per set: synthetic smoke test; calibration; calibration-2 (seen data); held-out round 2 (TP/FP/FN, P/R, n=155, per-repo, gap list); CryptoAPI-Bench mapped subset (with its required sentence). | "AI-assisted draft labels, human review pending"; never one merged number |
| 9 | **ML & AI** | CESNET model vs majority vs rule baselines ("not a PQC model"). Purpose triage vs rules ("loses to rules → not used"). Assistant chat box: answer, citations, **mode badge**, usage counter. **Cloud AI: ON/OFF** badge. | Chat runs TEMPLATE_FALLBACK unless the operator explicitly enabled cloud mode for the agent service; cloud eval 18/24 shown beside template 24/24 |
| 10 | **Claims & limits** | Claims register rendered read-only; "claims we must not make" list; what was not tested | No "production ready", "compliant", "certified", "quantum-safe guaranteed" |

**Run actions** (Overview page, collapsed, operator only):
- **Fixed allow-list:** `inventory_v11` on demo_bank_app, `member3_pipeline`, `evaluate_agent` (template), `snapshot`.
- **Execution:** argument lists, no `shell=True`, a 300 s timeout, redacted output, results written to `scratch/derived/`.
- **Scanning another folder** requires the checkbox "I am authorized to scan this". The scanner never opens or shows `.env`, `qcloud.env`, `*.pem`, `*.key` or `*.p12`.

**Export:** a Markdown + JSON report of the current view, written to `scratch/derived/ui-export/`. Streamlit's own download button is used, with no custom HTML.

## 4. Tests planned (D4)

- **Unit:** adapter (missing / mismatch / unknown status), `escaped_text`, badge mapping, approve-button enable logic with "TEST-ONLY", command allow-list (rejects anything else, no shell).
- **Streamlit `AppTest` smoke test per page** with real data, with a missing file, and with hostile strings (`<script>alert(1)</script>`, `../../etc/passwd`, a 10,000-character snippet).
- **Binding:** check that the server listens only on 127.0.0.1.
- **Code checks:** grep the UI code for `.env` access; check outputs against `verify_repo.py` secret patterns.
- **Screenshots:** recorded as **PLANNED** unless browser tooling already exists (I will ask before any download).

## 5. Five-minute demo script

| Time | Page | Say / show |
|---|---|---|
| 0:00 | 1 Overview | The problem in one line. The pipeline strip, the honesty banner, and that 3 of 6 steps are READY and why. |
| 0:40 | 3 Inventory | Filter "only HOLD": auth_gateway's RSA key type has unknown purpose, so the plan holds it. Open one snippet. |
| 1:20 | 4 Dependencies | OBSERVED edges with file:line versus DECLARED edges; 3 conflicts the descriptor missed. |
| 2:00 | 5 Plan | The waves, plus baseline = QpiAI Opt local solve (299.1, equal). QAOA on the simulator gives no advantage, and we say so. |
| 2:40 | 6 Verification | BEFORE X25519 vs AFTER X25519MLKEM768 (+~1.1 kB). Negative cases blocked: classical client vs hybrid-only server. |
| 3:30 | 7 Approval & rollback | The Approve button is disabled for a PROPOSED step; the rollback rehearsal result and the 3DES warning. |
| 4:10 | 8 / 9 | Held-out recall 0.116 (honest gaps). Assistant: ask "Which gates block ledger_audit?" and show the mode badge. |
| 4:45 | 10 Claims | What we do **not** claim. Close. |

**Fallback plan:**
- **Demo mode:** a frozen snapshot of real outputs works offline.
- **Screenshots:** if captured, they go in `assets/screenshots/`.
- **Markdown export:** of every page.
- **If Streamlit fails:** present `reports/member3/summary.md` and the executed notebooks in `scratch/derived/executed/`.

## 6. Files this will create (all new, Member 4 area)

`src/cryptoshift/ui/console/` (`app.py`, `data.py`, `components.py`, `pages/01_…10_*.py`, `sample/`), `scripts/run_ui.ps1`,
`tests/test_member4_ui.py`, `docs/member4/{README,demo-runbook,handoff}.md`, `requirements-ui.txt` (pins only what
is already installed; nothing new to download).
