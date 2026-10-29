# CryptoShift Web App v2: design (for approval; no UI code yet)

Wireframe: [`wireframe.html`](wireframe.html). It is a single self-contained page with no network calls; open it in a browser. It shows the glass shell, one dashboard card layout, the procedural background and the fallback switches.

Status: PLANNED. Hackathon prototype for mentors and judges.

## 1. Look and feel: "quantum lab", dark first

**Glass surfaces.** Panels are layered and translucent:
- `backdrop-filter: blur() saturate(160%)`;
- a 1 px gradient border (top-left highlight to transparent) that imitates a specular edge;
- an inner glow (`inset 0 1px 0 rgba(255,255,255,.08)`) and a soft depth shadow;
- 16 px radius;
- hover lifts by 2 px with `transform` only, and press settles back. Transitions use a spring-like `cubic-bezier(.2,.8,.2,1)` over 220 ms.

**Refraction.** Optional, and only on the top bar and the hero card. It is an SVG `feTurbulence` + `feDisplacementMap` filter applied as **progressive enhancement**. It is off by default when reduced motion, reduced transparency or high contrast is requested, and off in browsers without SVG filter support for backdrop.

**Blur budget.**

| Surface | Blur | Saturation | Alpha (dark / light) |
|---|---|---|---|
| sidebar | 20 px | 160% | .62 / .70 |
| top bar | 16 px | 160% | .62 / .70 |
| card | 14 px | 150% | .62 / .70 |
| drawer / modal | 24 px | 170% | .78 / .85 |
| tooltip | none (solid) | – | 1 / 1 |

- **Stacking:** at most **3** blur layers are visible at once (sidebar, top bar, one overlay). A drawer or modal disables card blur behind it, and nested `backdrop-filter` is never used: children of a glass panel are solid or transparent.
- **Performance:** only `transform` and `opacity` animate. The frame rate is measured on the heaviest page (Inventory with the full table) in Phase 5.

## 2. Design tokens (one file: `web/src/styles/tokens.css`, mirrored in `tailwind.config`)

| Token | Dark | Light |
|---|---|---|
| `--bg` | `#05080f` | `#eef2f8` |
| `--glass` | `rgba(16,24,40,.62)` | `rgba(255,255,255,.70)` |
| `--scrim` (behind text-heavy panels) | `rgba(7,11,20,.55)` | `rgba(244,247,252,.55)` |
| `--text` | `#e8edf6` | `#0f1726` |
| `--muted` | `#aeb9cc` | `#44506a` |
| `--accent` (only accent) | `#8ab4ff` | `#2349b8` |
| `--ok` / `--warn` / `--bad` | `#56d364` / `#e3b341` / `#ff7b72` | `#116329` / `#7a4a00` / `#a40e26` |
| `--sim` / `--info` / `--neutral` | `#c9a8ff` / `#79c0ff` / `#aeb9cc` | `#5a32a3` / `#0550ae` / `#44506a` |

- **Spacing:** 4-px scale (4, 8, 12, 16, 24, 32, 48).
- **Radius:** 8 / 12 / 16 / 24.
- **Elevation:** `e1` (0 1px 2px), `e2` (0 8px 24px / .25), `e3` (0 24px 64px / .35).
- **Motion:** 120 / 220 / 400 ms.
- **Type** (Inter, self-hosted): 12 / 14 / 16 (body) / 20 / 24 / 32. Numbers and code use JetBrains Mono.

**Computed contrast.** These are WCAG ratios of each text token on glass + scrim, composited over the background's **brightest** region (dark theme `#4a3f9c` nebula highlight; light theme `#ffffff`) and its darkest region:

| Theme | Region | Minimum ratio (token) | Body text ratio |
|---|---|---|---|
| dark | brightest | **6.93** (`--bad`) | 14.86 |
| dark | darkest | 7.65 (`--bad`) | 16.41 |
| light | brightest | 7.11 (`--ok`) | 17.25 |
| light | darkest | **6.50** (`--ok`) | 15.76 |

All are above AA (4.5:1 for body text, 3:1 for large text and UI parts). Phase 5 adds an automated test that recomputes these from the built CSS and fails the build below AA.

## 3. Accessibility and fallbacks (mandatory)

| Condition | What happens |
|---|---|
| `@supports not (backdrop-filter: blur(1px))` | glass becomes solid `--surface-solid` (`#121a2a` / `#ffffff`) |
| `prefers-reduced-transparency: reduce` or the in-app "Reduce transparency" toggle | solid surfaces; background dimmed to 30% |
| `prefers-contrast: more` or the in-app "High contrast" toggle | solid surfaces, 2 px borders, text `#ffffff` / `#000000`, no gradients |
| `forced-colors: active` | system colours, borders kept, background hidden |
| `prefers-reduced-motion: reduce` or the in-app toggle | **all** animation off; the background renders one static frame |

**Always on:**
- Focus ring: 2 px `--accent` + 2 px offset, visible on glass.
- Full keyboard navigation: skip link, sidebar arrow keys, Ctrl+K palette, Esc closes drawers and modals, focus is trapped in modals (Radix).
- Badges are **text + icon**, never colour alone (§6).
- Every chart has a "Data behind this chart" table.

## 4. Background (decorative, never evidence)

**What it is.** An **original, procedurally generated** scene: a canvas 2D layer under one SVG layer. It contains:
- **Qubit lattice:** a faint hex grid of points (opacity ≤ .18) with sparse "entanglement" links.
- **Bloch-sphere rings:** 3–4 thin ellipses at different tilts, slowly rotating (one revolution in about 120 s).
- **Interference waves:** two sine families whose sum is drawn as faint contour lines (phase drift about 0.02 rad/s).
- **Nebula:** 3 radial gradients (violet `#4a3f9c`, teal `#0f4c5c`, deep blue) at 20–35% opacity.

**Behaviour:**
- The scene is generated from a fixed seed, so it is the same on every load.
- It is static when reduced motion is set, and paused when the tab is hidden.
- It is capped at 30 fps.
- The legibility scrim always sits between it and the content.

**What it is not.** No photos, no product images, no logos (IBM, Google, QpiAI or others). No image is downloaded. If you later want a photo background, I will ask first and record its URL, author, licence and SHA-256 in `docs/webapp/assets.md`.

**Footer on every page:** "Background is a decorative illustration. QpiAI QCloud results shown are simulator runs."

## 5. Components

App shell (collapsible sidebar + top bar with data-mode chip, theme switch and "Cloud AI: ON/OFF"), command palette (Ctrl+K: pages, actions, finding IDs), glass card, KPI tile, data table (TanStack Table: sort, filter, column picker, virtualised rows, sticky header), status badge, provenance badge, confidence meter (●●○ + text), evidence drawer, toasts (aria-live polite), modal (Radix Dialog), tabs, tooltip, empty / loading (skeleton) / error states, charts (Recharts, each with a data table), wave timeline (Gantt-style, one row per service), patch-diff viewer (unified diff, plain text, preview only), trace viewer (BEFORE / AFTER side by side: protocol, group, cipher, bytes, command line), approval dialog.

**Evidence drawer.** Clicking any number, or the ⓘ next to it, opens a drawer with:
- the source file, producer, status label and modified time;
- the SHA-256 of the file and the command that regenerates it;
- for findings, the `file:line` and the escaped snippet.

**Approval dialog.** It is enabled only when the backend says the step is READY and every required gate is PASS. It requires:
- a typed approver name;
- the typed plan-hash prefix (≥12 characters), checked live against the plan hash;
- an "I understand this records my approval" checkbox.

It never offers "approve all".

## 6. Badges (text + icon + colour)

| Badge | Icon | Colour | Meaning |
|---|---|---|---|
| VERIFIED | ✔ | ok | built and observed with command evidence |
| PARTIAL | ◐ | warn | partly done; reason shown |
| MOCKED | ⚠ | neutral | fake data stands in |
| SIMULATED / SIMULATOR | ⚛ | sim | simulator run, not hardware |
| SYNTHETIC | 🧪 | neutral | invented demo data |
| PLANNED | ⏳ | info | not built yet |
| BLOCKED | ⛔ | bad | cannot run; reason shown |
| UNKNOWN | ? | neutral | an unrecognised value (never shown as passed) |
| OBSERVED / DECLARED / INFERRED | 👁 / 📄 / ↯ | ok / neutral / warn | edge provenance |
| HOLD | ◐ | warn | unknown purpose: human review |

## 7. Pages (12)

| # | Page | One-line purpose | Tier |
|---|---|---|---|
| 1 | Overview | Pipeline strip with the real status per stage, key counts, plan hash and the honesty banner | 1 |
| 2 | Data & evidence sources | Which datasets and public repos feed the evidence, with licence, commit and type (REAL public / SYNTHETIC / benchmark) | 2 |
| 3 | Inventory | Every finding with `file:line`, service and basis, purpose, confidence, ambiguity and candidate (for human review; unknown purpose = HOLD) | 1 |
| 4 | Dependencies | Graph with OBSERVED solid, DECLARED dashed and INFERRED dotted edges, a text legend, a text edge list, unknown endpoints and conflicts | 2 |
| 5 | Migration plan | Wave timeline with reasons; baseline vs QpiAI Opt (equal, not better) vs QCloud **simulator**; risk "provisional, not validated" | 1 |
| 6 | Verification | Gate matrix, compatibility matrix with negative cases, TEST SCENARIO traces, overhead with environment | 1 |
| 7 | Approval & rollback | Approve one READY step (human only), approval records and invalidation, the rollback record and rehearsal | 1 |
| 8 | Detection evaluation | TP/FP/FN, P/R and n per set kept separate; "not yet measurable at defensible size" where true; AI-draft label notice | 2 |
| 9 | ML & AI | Models beside baselines, "CESNET model is not a PQC model", the assistant drawer with mode badge, usage counter and Cloud AI ON/OFF | 2 |
| 10 | Claims & limits | The claims register plus "claims we must not make" | 1 |
| 11 | Audit log | Hash-chained entries and a "Verify chain" button with the result | 1 |
| 12 | Settings | Data mode (LIVE/DEMO), scan roots, cloud for custom scans (default OFF), theme and accessibility toggles; approver role to change | 1 |

**Layout:**
- **Widths:** 12-column grid at ≥1440 px; 8 columns at 1280 px; 1 column under 1024 px (small laptop). Mobile is out of scope.
- **Content width:** 1360 px maximum.
- **Long text:** tables scroll horizontally inside their card; cards never clip text.

## 8. Five-minute demo script

| Time | Page | Show |
|---|---|---|
| 0:00 | Overview | The problem in one line; the pipeline strip; 3/6 READY and why; the honesty banner; DEMO chip if offline |
| 0:40 | Inventory | Filter HOLD: auth_gateway's RSA key type has unknown purpose, so HOLD. Open the evidence drawer (file:line, hash, command). |
| 1:20 | Dependencies | OBSERVED edges with file:line vs DECLARED; the 3 conflicts the descriptor missed |
| 2:00 | Migration plan | Wave timeline; baseline = QpiAI Opt (299.1, **equal**); QAOA ⚛ SIMULATOR P(opt) 0.085 vs uniform 0.0625: no advantage |
| 2:40 | Verification | X25519 vs X25519MLKEM768 traces (+~1.1 kB); negative cases blocked |
| 3:20 | Approval & rollback | The approve dialog stays disabled for a PROPOSED step; approve a READY step as `approver`; it appears in the audit log; Verify chain = valid |
| 4:10 | Detection eval / ML & AI | Held-out recall 0.116 with the gaps; ask the assistant, showing the mode badge and Cloud AI OFF |
| 4:45 | Claims & limits | What we do not claim. Close. |

**Fallback plan:**
- **Demo mode:** reads the frozen snapshot of real outputs and works without network.
- **Screenshots:** in `docs/webapp/screens/`, only if captured from real runs.
- **Legacy console:** the Streamlit console (`scripts\run_ui.ps1`) remains as a backup.
- **Reports:** `reports/member3/summary.md` as the last resort.
