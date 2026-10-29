# Real banking PQC dataset

This folder contains only a filtered subset of an original published TLS measurement dataset. It contains no generated or synthetic observations and no repeated target IDs.

## Included file

`bank_tls_pqc_observations.csv` contains one row per source-provided banking target in the 2026-10-02 run. The data source identifies targets by anonymized IDs (`h###`), not bank names or hostnames.

- Source: [Global PQ Readiness Index](https://github.com/xuxu298/PQReadinessIndex), commit `1d08f843fd929d270e9e0924a258510b0be6815d`.
- Source data license: CC BY 4.0; attribution: Nguyen Dong, *PQReadinessIndex*.
- Original run: 350 public TLS endpoint observations across sectors; this extract retains the source rows tagged `banking` and cross-checks target IDs against the original `targets.csv`.
- Included bank-sector rows: 64 unique target IDs. Statuses copied from the source: 49 `PQ-SAFE`, 3 `CLASSICAL`, 12 `ERROR`.
- The study’s fixed comparison cohort is a different denominator: its published cross-run table uses 50 banking hosts. Do not report the 64-row single-run extract as the same cohort or compare its counts directly with that table.

## Meaning and limits

The source describes active TLS 1.3 ClientHello probes of public endpoints. `PQ-SAFE` means the probe negotiated the hybrid key-establishment group reported in `negotiated_group` (in these records, `X25519MLKEM768`). `CLASSICAL` means a classical group was negotiated. `ERROR` means the probe did not complete; it is not a negative PQC label and must not be counted as a classical result.

This is real, bank-sector **public-edge TLS** data. It is not bank application source code, an internal cryptographic bill of materials, a list of named banks, or evidence of a bank’s migration program. It covers key establishment only; it does not measure ML-DSA signatures, internal service dependencies, migration sequence, rollback readiness, or business criticality. Use it to demonstrate real sector context and public-edge protocol status, not to train a code scanner or claim bank-wide PQC readiness.

## Reproduce the filtered extract

The original source files are retained locally under the Git-ignored `data/public/raw/pq-readiness-index/` directory. The extractor verifies the source commit inputs, matches every banking result ID to the source target list, rejects duplicate IDs, and writes the CSV and manifest:

```powershell
.\.venv\Scripts\python.exe scripts\extract_bank_pqc_observations.py
```

See `dataset_manifest.json` for source, commit, row counts, status counts, and caveats. Only this filtered CSV and its manifest belong in the project dataset; the full multi-sector raw files stay local.
