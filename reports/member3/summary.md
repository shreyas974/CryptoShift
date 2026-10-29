# Member 3 results (2026-10-29)

All numbers are from real runs on this machine (Windows 11, i5-11400H, 15.7 GB RAM, Python 3.12.14, OpenSSL 3.5.9
Git-bundled). Raw outputs: `scratch/derived/member3/*.json` (git-ignored); transcripts:
`docs/evidence/member3-log.md`. The demo bank is SYNTHETIC.

## Planning (from scanner findings) — VERIFIED on synthetic inputs

| Item | Result |
|---|---|
| Merged findings / services | 14 findings (Member 2 inventory v1.1 + legacy scanner); 6 services (4 OBSERVED with scanned files, 2 DECLARED_ONLY) |
| Dependency edges | OBSERVED 4 (from Member 2 relationship evidence, file + line), DECLARED 5, INFERRED 0; cycles 0; unknown endpoints 0 on the demo bank (the SYNTHETIC multi-service fixture shows 9 OBSERVED edges and 3 unknown references) |
| Observed-vs-declared conflicts | 3 (e.g. nginx proxies `interbank_tls` → `ledger_audit`, not in the descriptor) |
| Risk score (PROVISIONAL, UNVALIDATED) | interbank_tls 13.5, auth_gateway 13.3, settlement_batch 7.85, payment_signing 7.8, ledger_audit 7.75, card_vault 5.9 |
| Sensitivity (each weight ×0.5 / ×1.5, 10 runs) | rank changed 6/10, **schedule changed 3/10**, min Kendall τ 0.47. The order depends on the provisional weights. |

## Scheduling: baseline VERIFIED, QpiAI Opt local solve VERIFIED (equal, not better), QAOA SIMULATOR

| Solver | Result |
|---|---|
| Deterministic exact baseline | feasible; objective 299.1; W0 interbank_tls + ledger_audit, W1 auth_gateway + payment_signing, W2 card_vault + settlement_batch; dependency violations 0; 7 ms |
| QpiAI Opt 0.0.9 (offline) | `classify` = MILP; 18 binary variables, 20 constraints; baseline assignment feasible in the Opt model |
| QpiAI Opt `solve(mode="local")`, owner-approved 2026-10-29 | status **optimal**, execution_mode local; objective **299.1 = baseline** (difference 0.0), same assignment; solver time 0.044 s (0.97 s incl. online key verification). No platform, submit() or QPU. |
| Reproduction of reported −13.07 | reproduced (existing module unchanged), but its bit decoding is reversed and its metric (best feasible sample) is weak |
| QAOA(reps=1, fixed angles) on Wave-0, QpiAI-QSV-Local, 1024 shots | exact optimum {interbank_tls, ledger_audit} (energy −21.25) = baseline Wave 0; P(optimum) 0.085 vs uniform 0.0625; most frequent sample infeasible ({auth_gateway, interbank_tls}, 116 shots); feasible shots 33.6% |

The Opt solver confirms the baseline is optimal for this model. No advantage over the baseline is shown; none is
claimed. (Objective moved from 292.8 to 299.1 because Member 2's detectors now find more evidence in the demo configs.)

## Verification — VERIFIED, TEST SCENARIO (loopback 127.0.0.1, throw-away keys)

| Check | Result |
|---|---|
| ML-KEM-768 round-trip self-test (OpenSSL CLI; python `cryptography`) | PASS / PASS (ciphertext 1088 B, secret 32 B) — not NIST KATs |
| ML-DSA-65 sign/verify self-test (both) | PASS / PASS (signature 3309 B, tampered message rejected) — not NIST KATs |
| Deterministic FIPS 203/204 seed KAT vectors (`from_seed_bytes`) | PASS / PASS (`ML-KEM-768` pubkey 1184 B, SHA-256 `0b7934c8...`; `ML-DSA-65` pubkey 1952 B, SHA-256 `d666806e...`) |
| Per-service PQC stack integration checks | PASS / PASS (`card_vault` KMS DEK envelope wrapping `ML-KEM-768 + HKDF-SHA256 + AES-256-GCM`; `auth_gateway`/`payment_signing` `ML-DSA-65` JWS token signing + tamper rejection) |
| Pure in-process primitive timing (`cryptography`, 40 reps) | VERIFIED in microseconds (`X25519`, `ML-KEM-768`, `RSA-2048-OAEP`, `ECDSA-P256`, `ML-DSA-65`, `RSA-2048-PSS` without OS process start-up noise) |
| Before trace (X25519) | TLS 1.3, X25519, TLS_AES_256_GCM_SHA384; client read 757 B / wrote 388 B |
| After trace (X25519MLKEM768) | TLS 1.3, X25519MLKEM768; read 1843 B / wrote 1564 B |
| After trace with ML-DSA-65 certificate | negotiated; peer signature `mldsa65`; read 10,207 B / wrote 1564 B |
| Compatibility matrix | 11/11 matched expectation (4 positive incl. 2 fallbacks; 7 negative correctly rejected: classical client vs hybrid-only server, TLS 1.2-only client, mismatched group, no common group, expired cert, untrusted cert; + trusted-cert positive) |
| Overhead (5 warm-up + 30 measured per config; wall time of one `s_client` process) | run 1: median 77.5 ms classical vs 79.45 ms hybrid; run 2: 96.06 vs 95.18 ms (p95 217 vs 121 ms). Process start-up dominates; timing differences are noise. Bytes are stable: +1086–1088 B read, +1176 B written |
| Rollback rehearsal (copy of nginx profile) | forced failure detected, restored hash matches snapshot, classical recovery handshake OK, original file unchanged; warning: restored profile still enables 3DES |
| Gate states | READY: card_vault, interbank_tls, payment_signing (generic loopback evidence only); PROPOSED: auth_gateway (new RSA finding with unknown purpose, HOLD), ledger_audit, settlement_batch (purpose unresolved, no scanned evidence) |
| Approvals | none (human-only CLI; tests use "TEST-ONLY" in temp stores) |

## Machine learning

| Track | Result |
|---|---|
| A — CESNET service category (traffic demo; **not crypto/PQC labels**) | split by day (train 4–10 Oct, test 11–17 Oct 2021; 105,000 rows each); HistGradientBoosting accuracy 0.813 / macro-F1 0.748 vs majority 0.118 / 0.010 and BYTES_REV-bin rule 0.246 / 0.127 |
| B — finding-purpose triage | 79 rows, 8 repos (now includes round-2 draft labels), leave-one-repo-out: model accuracy 0.646 / macro-F1 0.273; rule engine 0.519 / 0.783; majority 0.658 / 0.132. **Does not beat the rules → rules kept; suggestions unused.** |
| C — banking observations by date | descriptive chart only (notebook 01) |

## CryptoShift Assistant: cloud LLM (Sarvam) with local read-only tools

| Mode | Result (24 fixed questions) |
|---|---|
| TEMPLATE_FALLBACK | 24/24 (cites 10/10, role 3/3, refuse 6/6, unknown 3/3, injection 2/2); bundle and approvals unchanged |
| SARVAM_CLOUD, sarvam-105b, one owner-approved live run | 24/24 on v2 checks, **18/24 on the stricter v3 check**: 8 answers came from the cloud, only 1 substantive, 6 said "unknown" despite evidence. 17 requests, 8,701 + 2,013 tokens, estimated **₹0.25** (cap ₹0.75). Injection not followed. |

Details and the cloud data policy: `docs/member3/agent.md`. Service bound to 127.0.0.1:8765.

## Notebooks (100% Visual Form)

All 10 notebooks in `notebooks/member3/01..10.ipynb` (as well as `scratch/derived/executed/01..10.ipynb`) are rendered in pure visual form with 30 embedded high-DPI PNG figures (`assets/diagrams/member3/*.png` and `scratch/derived/member3/figs/*.png`) generated by `src/cryptoshift/notebook_visuals.py` and `scripts/build_member3_notebooks.py`.
