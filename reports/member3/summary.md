# Member 3 results (2026-10-29)

All numbers are from real runs on this machine (Windows 11, i5-11400H, 15.7 GB RAM, Python 3.12.14, OpenSSL 3.5.9
Git-bundled). Raw outputs: `scratch/derived/member3/*.json` (git-ignored); transcripts:
`docs/evidence/member3-log.md`. The demo bank is SYNTHETIC.

## Planning (from scanner findings) — VERIFIED on synthetic inputs

| Item | Result |
|---|---|
| Merged findings / services | 12 findings; 6 services (4 OBSERVED with scanned files, 2 DECLARED_ONLY) |
| Dependency edges | OBSERVED 4 (file + line), DECLARED 5, INFERRED 0; cycles 0; unknown endpoints 0 |
| Observed-vs-declared conflicts | 3 (e.g. nginx proxies `interbank_tls` → `ledger_audit`, not in the descriptor) |
| Risk score (PROVISIONAL, UNVALIDATED) | interbank_tls 13.5, auth_gateway 11.5, settlement_batch 7.85, payment_signing 7.8, ledger_audit 7.75, card_vault 5.9 |
| Sensitivity (each weight ×0.5 / ×1.5, 10 runs) | rank changed 5/10, schedule changed 0/10, min Kendall τ 0.6 |

## Scheduling — baseline VERIFIED, QpiAI Opt solve BLOCKED, QAOA SIMULATOR

| Solver | Result |
|---|---|
| Deterministic exact baseline | feasible; objective 292.8; W0 interbank_tls + ledger_audit, W1 auth_gateway + payment_signing, W2 card_vault + settlement_batch; dependency violations 0; 3.1 ms |
| QpiAI Opt 0.0.9 (offline) | `classify` = MILP; 18 binary variables, 20 constraints; baseline assignment feasible in the Opt model |
| QpiAI Opt `solve(mode="local")` | **BLOCKED** — not authorized in this session and no key in the environment |
| Reproduction of reported −13.07 | reproduced (existing module unchanged) — but its bit decoding is reversed and its metric (best feasible sample) is weak |
| QAOA(reps=1, fixed angles) on Phase 2 Wave-0, QpiAI-QSV-Local, 1024 shots | exact optimum {interbank_tls, ledger_audit} (energy −21.25) = baseline Wave 0; P(optimum) 0.080 vs uniform 0.0625; most frequent sample infeasible (all four, 108 shots); feasible shots 31.5% |

No advantage over the baseline is shown; none is claimed.

## Verification — VERIFIED, TEST SCENARIO (loopback 127.0.0.1, throw-away keys)

| Check | Result |
|---|---|
| ML-KEM-768 round-trip self-test (OpenSSL CLI; python `cryptography`) | PASS / PASS (ciphertext 1088 B, secret 32 B) — not NIST KATs |
| ML-DSA-65 sign/verify self-test (both) | PASS / PASS (signature 3309 B, tampered message rejected) — not NIST KATs |
| Before trace (X25519) | TLS 1.3, X25519, TLS_AES_256_GCM_SHA384; client read 757 B / wrote 388 B |
| After trace (X25519MLKEM768) | TLS 1.3, X25519MLKEM768; read 1843 B / wrote 1564 B |
| After trace with ML-DSA-65 certificate | negotiated; peer signature `mldsa65`; read 10,207 B / wrote 1564 B |
| Compatibility matrix | 11/11 matched expectation (4 positive incl. 2 fallbacks; 7 negative correctly rejected: classical client vs hybrid-only server, TLS 1.2-only client, mismatched group, no common group, expired cert, untrusted cert; + trusted-cert positive) |
| Overhead (5 warm-up + 30 measured per config; wall time of one `s_client` process) | run 1: median 77.5 ms classical vs 79.45 ms hybrid; run 2: 96.06 vs 95.18 ms (p95 217 vs 121 ms). Process start-up dominates; timing differences are noise. Bytes are stable: +1086–1088 B read, +1176 B written |
| Rollback rehearsal (copy of nginx profile) | forced failure detected, restored hash matches snapshot, classical recovery handshake OK, original file unchanged; warning: restored profile still enables 3DES |
| Gate states | READY: auth_gateway, card_vault, interbank_tls, payment_signing (generic loopback evidence only); PROPOSED: ledger_audit, settlement_batch (purpose unresolved — no scanned evidence) |
| Approvals | none (human-only CLI; tests use "TEST-ONLY" in temp stores) |

## Machine learning

| Track | Result |
|---|---|
| A — CESNET service category (traffic demo; **not crypto/PQC labels**) | split by day (train 4–10 Oct, test 11–17 Oct 2021; 105,000 rows each); HistGradientBoosting accuracy 0.813 / macro-F1 0.748 vs majority 0.118 / 0.010 and BYTES_REV-bin rule 0.246 / 0.127 |
| B — finding-purpose triage | 59 rows, 5 repos, leave-one-repo-out: model accuracy 0.644 / macro-F1 0.400; rule engine 0.593 / 0.810; majority 0.153 / 0.044. **Does not beat the rules → rules kept; suggestions unused.** |
| C — banking observations by date | descriptive chart only (notebook 01) |

## Local agent — template back-end VERIFIED, LLM BLOCKED

24 fixed questions. Run 1: 24/24 on v1 checks but 3 wrong-topic answers found on manual review (true 21/24).
After a routing fix and an added expected-tool check (logged): 24/24 (cites 10/10, role 3/3, refuse 6/6,
unknown 3/3, injection 2/2); bundle and approvals unchanged. Service bound to 127.0.0.1:8765.

## Notebooks

All 10 notebooks in `notebooks/member3/` executed end to end with `jupyter nbconvert --execute` (exit 0, 10–35 s
each) into `scratch/derived/executed/`; committed copies have outputs cleared.
