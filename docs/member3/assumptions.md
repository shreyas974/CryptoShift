# Member 3 assumptions register

Every number below is an **ASSUMPTION** unless the "Source" column says it came from data. Change values in
`src/cryptoshift/planning/planning_config.json` (planning) or the gate config in `src/cryptoshift/gates/` (verification).

## Planning and scheduling

| Item | Value | Source |
|---|---|---|
| Risk weights: crypto_exposure / network_exposure / criticality / dependents / verification_readiness | 3.0 / 1.5 / 2.0 / 1.5 / 0.5 | ASSUMPTION (hand-set; not fitted) |
| Algorithm class points (Shor key establishment / Shor signature / asymmetric unknown purpose / legacy symmetric / weak hash / legacy protocol / other) | 1.0 / 0.8 / 0.6 / 0.5 / 0.4 / 0.4 / 0.2 | ASSUMPTION (key establishment ranked above signatures because of harvest-now-decrypt-later) |
| Crypto exposure cap | 3.0 | ASSUMPTION |
| Criticality points (CRITICAL/HIGH/MEDIUM/LOW/unknown) | 1.0/0.7/0.4/0.2/0.5 | ASSUMPTION; the criticality *labels* come from YAML (OBSERVED) or the synthetic descriptor (DECLARED) |
| Network exposure | 1.0 if `listen`/`server_name`/`ssl_certificate`/`tls_listener` seen in the service's files, 0.0 otherwise, 0.5 if no files | ASSUMPTION (keyword heuristic) |
| Number of waves | 3 | ASSUMPTION |
| Max services per wave | 2 | ASSUMPTION |
| Maintenance window per wave | 85 minutes | ASSUMPTION |
| Risk-delay weight in objective | 3.5 | ASSUMPTION (unchanged from the existing scheduler) |
| Per-service duration (minutes) and rollout cost | from `demo_bank_app/services.py` | DECLARED (synthetic); default 45 min / 20.0 if absent = ASSUMPTION |
| Wave-0 verification readiness | YAML `verification_ready_wave0` if present, else descriptor | OBSERVED (synthetic config) / DECLARED |
| Enforced dependency edges | OBSERVED + DECLARED; INFERRED edges reported but not enforced | ASSUMPTION |
| Edge direction | provider (upstream) migrates no later than consumer (downstream) | ASSUMPTION (same rule as the existing scheduler) |

## Verification (Phase 4)

| Item | Value | Source |
|---|---|---|
| Overhead gate threshold | hybrid median handshake time ≤ 1.5 × classical median, and hybrid handshake bytes ≤ classical + 4096 B | ASSUMPTION |
| Handshake repetitions | 5 warm-up + 30 measured per configuration, fixed order | ASSUMPTION (method) |
| Required gates for READY | crypto self-test, hybrid handshake, compatibility matrix, overhead, rollback rehearsal | ASSUMPTION (policy) |

## Data provenance reminders

- The demo bank (`demo_bank_app/`) is SYNTHETIC. Plans built from it demonstrate the method, not a bank's estate.
- `ledger_audit` and `settlement_batch` have no scanned files; they enter the plan as `DECLARED_ONLY`.
