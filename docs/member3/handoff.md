# Member 3 handoff — planning, verification, rollback, QpiAI, ML, assistant

Results with numbers: [`reports/member3/summary.md`](../../reports/member3/summary.md). Command transcripts:
[`docs/evidence/member3-log.md`](../evidence/member3-log.md). Assumptions: [`assumptions.md`](assumptions.md).
JSON contract for Member 4: [`contract.md`](contract.md). Agent: [`agent.md`](agent.md).

## What was built (all new, Member 3-owned; existing modules unchanged)

| Area | Code | Status |
|---|---|---|
| Findings → tasks, provenance graph, provisional risk, sensitivity, scheduler adapter | `src/cryptoshift/planning/` (`findings.py`, `dependency_graph.py`, `risk.py`, `planner.py`, `planning_config.json`) | VERIFIED on synthetic demo bank |
| QpiAI Opt offline checks, QAOA reproduction + Phase 2 experiment | `src/cryptoshift/optimization/member3_qpiai.py`, `scripts/member3_phase3.py` (`--authorize-local-solve`) | Opt local solve VERIFIED once (optimal, equal to baseline); QAOA SIMULATOR |
| Loopback OpenSSL lab, deterministic KATs, service-stack checks, gates, approval, rollback rehearsal | `src/cryptoshift/gates/` (`openssl_lab.py`, `verification_gates.py`, `approval.py`, `rollback_rehearsal.py`), `scripts/member3_phase4.py`, `scripts/approve_plan.py` | VERIFIED, TEST SCENARIO |
| ML tracks A/B | `src/cryptoshift/ml/` (`cesnet_service.py`, `purpose_triage.py`), `scripts/member3_phase5.py` | VERIFIED (A demo; B negative result) |
| Assistant (cloud LLM (Sarvam) with local read-only tools) | `src/cryptoshift/agent/` (`sarvam.py` client, validator, budget guard), `scripts/run_agent.ps1`, `scripts/ask_agent.py`, `scripts/evaluate_agent.py` | TEMPLATE_FALLBACK 24/24; SARVAM_CLOUD one live run 18/24 (v3) + upgraded validator |
| End-to-end pipeline | `src/cryptoshift/member3_pipeline.py`, `scripts/member3_pipeline.py` | VERIFIED |
| Contract | `schemas/member3/`, `scripts/build_member3_contract.py` | VERIFIED (examples validate) |
| Container packaging | `docker/Dockerfile.agent`, `docker/Dockerfile.tls_lab`, `docker/docker-compose.yml` | VERIFIED (ready-to-build Dockerfiles) |
| Visual Notebooks | `notebooks/member3/01..10.ipynb`, `src/cryptoshift/notebook_visuals.py`, `scripts/build_member3_notebooks.py`, `assets/diagrams/member3/*.png` | VERIFIED (all 10 converted to pure visual form with 30 embedded figures) |
| Tests | `tests/test_member3_{planning,verification,agent,contract,sarvam}.py` | see evidence log |

## How to run

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-member3.txt
.\.venv\Scripts\python.exe scripts/member3_phase3.py            # scheduling comparison (offline)
.\.venv\Scripts\python.exe scripts/member3_phase4.py            # loopback verification evidence (~2 min)
.\.venv\Scripts\python.exe scripts/member3_phase5.py            # ML tracks A and B (~30 s)
.\.venv\Scripts\python.exe scripts/member3_pipeline.py          # plan -> reports/member3/plan.{json,md}
.\.venv\Scripts\python.exe scripts/evaluate_agent.py            # agent evaluation
.\.venv\Scripts\python.exe scripts/build_member3_contract.py    # schemas + validated examples
.\.venv\Scripts\python.exe scripts/approve_plan.py --status     # HUMAN approval tool (status only here)
# Notebooks (kernel "cryptoshift-m3"):
.\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute notebooks/member3/01_data_overview.ipynb `
  --ExecutePreprocessor.kernel_name=cryptoshift-m3 --output-dir scratch/derived/executed
.\.venv\Scripts\python.exe -m jupyter lab --no-browser --ip=127.0.0.1 --port=8899   # token auth; never share the URL
```

OpenSSL: the lab uses `C:\Program Files\Git\usr\bin\openssl.exe` (3.5.9) by full path, or `CRYPTOSHIFT_OPENSSL`.
Without OpenSSL 3.5+ the verification gates report BLOCKED and steps stay PROPOSED.

## Measured results and limits (short)

- Schedule objective 299.1, 0 dependency violations; risk score provisional (rank changed in 6/10 weight
  perturbations, schedule in 3/10). Dependency edges come from Member 2's OBSERVED relationship evidence.
- Loopback hybrid X25519MLKEM768 handshake works; +~1.1 kB each direction; ML-DSA-65 cert chain adds ~9.4 kB read.
  Timing comparisons are noise (process start-up); don't quote latency overhead.
- 11/11 compatibility cases as expected; rollback rehearsal recovers.
- READY = generic lab evidence, not service-stack verification. 3 services stay PROPOSED (auth_gateway: unknown-purpose RSA finding -> HOLD; 2 with no scanned evidence).
- QpiAI Opt local solve (owner-approved): optimal, objective 299.1 = baseline, same assignment (not better). QAOA fixed-angle: P(optimum) 0.085 vs 0.0625 uniform.
- CESNET classifier is a traffic demo; purpose-triage model loses to the rules.
- Assistant: template 24/24; Sarvam cloud run safe but over-cautious (6 'unknown' answers despite evidence), ~Rs 0.25.

## Completed additions & remaining scope boundaries

- COMPLETED: richer structured evidence (`structured_items`) for the Sarvam assistant and validator rule rejecting `'unknown'` despite non-empty cited evidence, plus false-alarm fixes for long repo paths and multi-clause role sentences (`src/cryptoshift/agent/sarvam.py`, `src/cryptoshift/agent/assistant.py`).
- COMPLETED: deterministic FIPS 203 (`ML-KEM-768`) & FIPS 204 (`ML-DSA-65`) seed KAT vector checks (`from_seed_bytes` SHA-256 verification), per-service KMS DEK envelope wrapping (`card_vault`) and JWS token signing (`auth_gateway`/`payment_signing`/`ledger_audit`) stack checks, and pure in-process microsecond primitive timing (`src/cryptoshift/gates/openssl_lab.py`).
- COMPLETED: Dockerfiles for the assistant and TLS verification lab (`docker/Dockerfile.agent`, `docker/Dockerfile.tls_lab`, `docker/docker-compose.yml`).
- COMPLETED: all 10 notebooks in `notebooks/member3/01..10.ipynb` converted to pure visual form with 30 embedded high-DPI charts (`src/cryptoshift/notebook_visuals.py`, `scripts/build_member3_notebooks.py`, `assets/diagrams/member3/*.png`).
- Known defect left in place for reproducibility: `optimization/qcloud_experiment.py` decodes bitstrings in reverse
  order (measured); `member3_qpiai.py` uses the corrected order.
