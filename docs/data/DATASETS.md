# CryptoShift datasets

Machine-readable registry: [`data/registry.json`](../../data/registry.json). This page explains what each dataset
is, what it is **not**, and how to use it safely. All datasets are read-only inputs.

## Where the data lives

Large external data is never committed. Point CryptoShift at it with environment variables (or the git-ignored
`.cryptoshift_datasets.local.json`):

| Variable | Meaning |
|---|---|
| `CRYPTOSHIFT_DATASET_DIR` | Root of the dataset pack (contains `manifest.json`, `CESNET-TLS22/`, `pqc_evidence/`) |
| `CRYPTOSHIFT_CESNET_H5_PATH` | Override for `CESNET-TLS22-S.h5` |
| `CRYPTOSHIFT_PQC_OBS_CSV_PATH` | Override for `banking_pqc_observations.csv` |

If none is set, the loader falls back to the default pack location used on the original development machine
(`src/cryptoshift/datasets.py:resolve_dataset_paths`). Derived output goes to `scratch/derived/` (git-ignored).

```powershell
.\.venv\Scripts\python.exe cryptoshift_cli.py data-summary            # writes scratch/derived/data-summary/
.\.venv\Scripts\python.exe cryptoshift_cli.py data-summary --max-stream-rows 20000 --chunk-size 5000
```

## 1. CESNET-TLS22 S — REAL TLS flow metadata

- **What it is:** 25,000,000 encrypted-TLS flow records from the CESNET2 network, 4–17 Oct 2021, 14 daily
  tables, 30 columns (packet/byte counts, durations, per-packet info, TCP flags, `APP`, `CATEGORY`).
- **Size / checksum:** 3,231,649,088 bytes; SHA-256 `36e3240b144bf8902e874e8fd875b6e7ac3e40b0706eb5f8d3f40720ff5a2e06`
  as recorded in the pack's `manifest.json` / `verification.json`. `data-summary` re-checks file size and row count
  (both match); the file was **not independently re-hashed** in this work.
- **License:** CC-BY-4.0. Cite: Jan Luxemburk and Tomáš Čejka, "Fine-grained TLS services classification with
  reject option", *Computer Networks* 220 (2023), 109467, doi:10.1016/j.comnet.2022.109467; dataset
  doi:10.5281/zenodo.10610895.
- **Use only for:** streaming, filtering and scale demonstrations.
- **It is NOT:** bank data; PQC ground truth; crypto labels (`APP`/`CATEGORY` are service labels). **Never compute
  detector precision/recall from it.**
- **Format note:** PyTables HDF5 with Blosc compression. h5py reads it only with `hdf5plugin` installed
  (installed in `.venv`). `data-summary` reads selected fields in bounded slices; it never loads all rows.

## 2. Banking PQC observations — REAL public-endpoint observations

- **What it is:** 320 public TLS 1.3 endpoint handshake observations: 64 pseudonymous banking hosts × 5 scan dates
  (2026-04-23, 2026-05-10, 2026-09-03, 2026-09-14, 2026-10-02). Status counts: PQ-SAFE 175, CLASSICAL 80, ERROR 65.
- **Checksum:** SHA-256 `2ac284d66b545d4df427e280116fa6f190ff8b3971a3e433a0bd4b5eb069f46e` (computed locally).
- **License:** CC-BY-4.0. Attribute Nguyen Dong, *Global PQ Readiness Index* (2026),
  https://github.com/xuxu298/PQReadinessIndex, and keep the scan file names.
- **Rules:**
  - Duplicate key = `(scan_file, host, ts)`. `data-summary` counts duplicates (0 found) instead of dropping them.
  - A host repeating on different dates is a valid observation and is kept.
  - Status values are kept unchanged. `ERROR` = unclassified (never "classical" or "negative").
- **Describe only as:** public-endpoint observations on the given dates. It says nothing about internal systems,
  signatures, certificates or a bank's migration status.

A 64-row single-date view (2026-10-02 run) is tracked at `data/real/bank_tls_pqc_observations.csv`
(see `data/real/dataset_manifest.json`).

## 3. Synthetic fixtures — SYNTHETIC

`data/fixtures/synthetic/` (11 labelled instances in `data/labels/synthetic_fixture_labels.json`) and
`demo_bank_app/` are hand-written. They are a **smoke test** for detector logic, not a benchmark, and are excluded
from every real-data metric.

## 4. Public code labels — REAL code, team annotations

Labelled lines from permissively licensed public repositories at pinned commits; see
[`data/labels/public_code/README.md`](../../data/labels/public_code/README.md) and the guidelines in
[`docs/data/labelling-guidelines.md`](labelling-guidelines.md). Third-party sources are fetched into the
git-ignored `data/public/raw/`; only pointers, labels and attributed licence info are committed.

## Known documentation gaps

`data/README.md` mentions `data/public/README.md`, `data/public/processed/licma_real_misuse_findings.csv` and
`data/labels/real_dataset_sources.json`; none of these files exist in the repository. Owner (Member 1) to fix or
remove those references.
