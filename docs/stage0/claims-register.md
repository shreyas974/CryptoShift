# Claims register

Every number we might say in a pitch, with its real status. If a claim is not listed here as VERIFIED, say it with
its label (e.g. "mocked", "synthetic smoke test") or do not say it. Evidence:
[`docs/evidence/stage0-stage1-log.md`](../evidence/stage0-stage1-log.md).

| Claim | Status | What was actually checked (2026-10-29) | How to say it |
|---|---|---|---|
| "13 findings across 6 services" | **VERIFIED as SYNTHETIC descriptor output** | `scan_banking_services()` returns 13 findings, 6 services, all `evidence_type=service_descriptor`; they come from the hard-coded `demo_bank_app/services.py` dict with synthetic line numbers — **not** a file scan. A real file scan of `demo_bank_app/configs/` gives 10 findings / 4 services (legacy `scan`) or 6 findings in the nginx file (new `inventory`). | "13 findings across 6 *synthetic* services from our demo descriptor." |
| "Precision/recall 0.875/0.875 (TP7 FP1 FN1 TN2)" | **SYNTHETIC SMOKE TEST** | Reproduced: 11 fixtures, TP 7 FP 1 FN 1 TN 2. Fixtures are hand-written and mostly declare algorithms as string constants. | "On an 11-file synthetic smoke test…" — never as a benchmark or real-world accuracy. |
| Detector P/R on real public code | **PARTIAL — not yet measurable at defensible size** | Held-out (3 repos, 8 files, 30 positives, labelled before the run): TP 28 FP 0 FN 2 → P 1.000 R 0.933 F1 0.966. Calibration (tuned on): TP 31 FP 0 FN 7. Single AI annotator who also wrote the detector; reviewer pending. | "Early sanity check on 30 labelled lines; not a benchmark." |
| "544 B vs 7661 B handshake" | **MOCKED / ANALYTICAL** | `protocol_demo.py` labels it `MOCKED_PROTOCOL_TRACE`; numbers are specification-derived estimates. No handshake was run. | "Estimated from FIPS 203/204 sizes." |
| "6/6 verification gates pass" | **MOCKED** | Reproduced 6/6, but the KAT/handshake/latency flags are constant `True` unless wave-0 readiness is false or a failure is simulated. | "Prototype gates (boolean placeholders) pass." |
| "Objective 248.105" | **VERIFIED for the deterministic fallback scheduler on synthetic tasks**; QpiAI MILP equality **REPORTED, NOT RE-VERIFIED** | Unit test `test_deterministic_fallback_scheduler_respects_dependencies_and_capacity` passes with 248.105. QpiAI Opt solve was not run here (needs credentials/`demo`). | "Our baseline scheduler's objective on the synthetic 6-service instance is 248.105." |
| "QAOA energy −13.07" | **REPORTED, NOT RE-VERIFIED** | Not run in this checkout (would require `demo`, which creates `.env`). Even when run it is a local classical statevector simulation. | Do not quote without re-running; never imply quantum advantage. |
| "CESNET-TLS22 S: 25,000,000 rows, 3,231,649,088 bytes" | **VERIFIED** (size and row count) | `data-summary`: 14 tables, 25,000,000 rows, size matches manifest. SHA-256 quoted from manifest, **not independently re-hashed**. | "Real 2021 TLS flow metadata used only for streaming/scale; not bank data." |
| "320 banking PQC observations, 5 dates" | **VERIFIED** | 320 rows, 64 hosts, 0 duplicate `(scan_file, host, ts)` keys, PQ-SAFE 175 / CLASSICAL 80 / ERROR 65. | "320 public-endpoint observations on 5 dates; ERROR = unclassified." |
| "Hybrid X25519MLKEM768 is available locally" | **FEASIBILITY ONLY** | Git-bundled OpenSSL 3.5.9 (not on PATH) lists `X25519MLKEM768`. No handshake run. | "A local hybrid handshake is feasible next." |
| "CBOM" | **PARTIAL** | Output is a CBOM-*like* JSON, not schema-validated. | Say "CBOM-like", never "CycloneDX". |
| Risk score | **PROVISIONAL, UNVALIDATED** | Formula documented in [requirements-traceability.md](requirements-traceability.md); weights hand-set. | Never call it scientific or calibrated. |

## README alignment

The top-level README's Key Capabilities section states these numbers; the README now links here and states that
statuses in this register take precedence.

## Member 3 additions (2026-10-29) — evidence: `docs/evidence/member3-log.md`, `reports/member3/summary.md`

| Claim | Status | What was checked | How to say it |
|---|---|---|---|
| Migration tasks are derived from scanner findings | **VERIFIED (synthetic inputs)** | `planning.planner`: 12 findings → 6 tasks with finding IDs; 2 services DECLARED_ONLY | "Tasks come from scanned evidence; two demo services have only declared data." |
| Dependency edges carry provenance | **VERIFIED** | 4 OBSERVED (file+line), 5 DECLARED, 0 INFERRED; 3 conflicts reported; cycle handling tested | — |
| Risk score | **PROVISIONAL, UNVALIDATED** | documented formula; sensitivity: rank changed 5/10, schedule 0/10 | Never "scientific" or "calibrated". |
| Deterministic schedule on the findings-derived problem | **VERIFIED** | objective 292.8, 0 dependency violations (constraints are assumptions) | — |
| QpiAI Opt solves the schedule | **BLOCKED** | offline classify/inspect/feasibility only (MILP, 18 vars, 20 constraints) | "Model validated offline; solve not run." |
| QAOA energy −13.07 | **REPRODUCED (SIMULATOR), with caveats** | existing module re-run; its bit decoding is reversed and its metric is weak | Prefer: "fixed-angle QAOA put 8.0% probability on the optimum vs 6.25% uniform." |
| Working before/after protocol traces | **VERIFIED, TEST SCENARIO (loopback, test keys)** | X25519 vs X25519MLKEM768 handshakes with OpenSSL 3.5.9; ML-DSA-65 certificate handshake also negotiated | Never "production traffic". |
| "544 B vs 7661 B" | still **MOCKED/ANALYTICAL** | superseded by measured loopback bytes: 757/388 B → 1843/1564 B (EC cert); 10,207 B read with ML-DSA-65 cert | Use the measured loopback numbers. |
| Compatibility tests | **VERIFIED (loopback)** | 11/11 cases incl. 7 negative cases | — |
| ML-KEM / ML-DSA self-tests | **VERIFIED as round-trip self-tests** | OpenSSL and `cryptography` both PASS | Not "NIST KAT validated". |
| Overhead | **PARTIAL** | bytes measured; timing dominated by process start-up (two runs disagree in direction) | Do not quote latency overhead. |
| Verification gates (Member 3 pipeline) | **VERIFIED (generic lab evidence)** | 4 steps READY, 2 PROPOSED; READY ≠ service-stack verified | "Eligible for human review." |
| "6/6 gates pass" (old prototype) | still **MOCKED** | old `verification.py` unchanged | Use the Member 3 gates instead. |
| Rollback rehearsal | **VERIFIED (on a copy, loopback)** | forced failure → restore → hash match → classical recovery | — |
| Human approval gate | **VERIFIED (tests only)** | approval bound to plan hash; change invalidates; no real approval recorded | — |
| CESNET classifier | **VERIFIED demo — not crypto** | macro-F1 0.748 vs 0.010 majority, split by day | "Traffic classification demo; says nothing about quantum readiness." |
| ML purpose triage | **VERIFIED negative result** | does not beat the rule engine (macro-F1 0.40 vs 0.81) | "Rules kept." |
| Local AI agent | **PARTIAL** | template back-end 24/24 (after a logged fix; first run 21/24 true); LLM BLOCKED | Never "AI model answers" — it is a deterministic template. |
