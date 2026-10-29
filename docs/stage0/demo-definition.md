# Demo definition (measurable)

A demo step passes only if the listed command produces the listed observable result. "Mocked" steps must be shown
with their label on screen.

| # | Step | Command | Pass criterion | Nature |
|---|---|---|---|---|
| 1 | Tests and hygiene | `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` and `scripts/verify_repo.py` | all tests OK; `Scan result: PASS` | VERIFIED |
| 2 | Real data summary | `cryptoshift_cli.py data-summary` | 320 rows, 5 scan dates, 0 duplicate keys, ERROR=65 shown as unclassified; CESNET 25,000,000 rows, size matches manifest; output under `scratch/derived/` | VERIFIED (real data) |
| 3 | Inventory of demo configs | `cryptoshift_cli.py inventory` | 6 findings in `interbank_tls_nginx.conf` with line numbers; JSON says "not CycloneDX" | VERIFIED (input is SYNTHETIC config) |
| 4 | Inventory of real public code | `cryptoshift_cli.py inventory --path data/public/raw/python-jose` (after `scripts/fetch_public_label_sources.py`) | findings with file:line, purpose, ambiguity; unknown purpose shows HOLD | VERIFIED (real code, not bank code) |
| 5 | Detector metrics | `scripts/evaluate_public_labels.py --split held_out` | prints TP/FP/FN, P/R/F1, sample size **and** "NOT YET MEASURABLE AT DEFENSIBLE SIZE" | PARTIAL (small, single annotator) |
| 6 | Wave schedule | `-m unittest tests.test_cryptoshift` (scheduler test) | objective 248.105, no dependency violations | VERIFIED on SYNTHETIC tasks |
| 7 | Verification gates / protocol trace | existing `demo` | must display `MOCKED_PROTOCOL_TRACE` and "prototype gate" text | MOCKED |
| 8 | Rollback | `test_mvp_vertical_slice_human_approval_staging_and_rollback` | simulated failure restores staged copy | PARTIAL (staged copy only) |

**Do not run during a live demo without preparation:** `demo`, `check-auth`, `init-env` (they create `.env` from
`.env.example` when it is missing) and `evaluate` / `mvp-slice` / `schedule` (they rewrite tracked report files).
