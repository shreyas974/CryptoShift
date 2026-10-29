# Setup (Windows PowerShell) — commands actually run on 2026-10-29

Full transcripts: [`docs/evidence/stage0-stage1-log.md`](../evidence/stage0-stage1-log.md). General QpiAI setup:
[`docs/setup/qpiai-shared-setup.md`](../setup/qpiai-shared-setup.md) (not needed for Stage 1).

## Requirements

- Python 3.11+ is the project target (`.venv` here: Python 3.12.14). Note: `pyproject.toml` still says `>=3.10`.
- Git (2.56 used here). OpenSSL on PATH is **not** required for Stage 1.

## Install (inside `.venv` only)

```powershell
.\.venv\Scripts\python.exe -m pip install h5py pyyaml tables numpy   # already present in this .venv
.\.venv\Scripts\python.exe -m pip install hdf5plugin cryptography    # added in Stage 1
```

Result here: `Successfully installed cryptography-50.0.2 hdf5plugin-7.1.0`.
`hdf5plugin` lets h5py decode the Blosc-compressed CESNET file; `cryptography` is used for certificate metadata.

## Dataset paths

Set (or leave unset to use the default pack location):

```powershell
$env:CRYPTOSHIFT_DATASET_DIR = "<path to cryptoshift_dataset>"
# optional overrides
$env:CRYPTOSHIFT_CESNET_H5_PATH = "<...>\CESNET-TLS22\S\CESNET-TLS22-S.h5"
$env:CRYPTOSHIFT_PQC_OBS_CSV_PATH = "<...>\pqc_evidence\banking_pqc_observations.csv"
```

## Safe commands and real results

| Command | Result on this machine |
|---|---|
| `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` | baseline: 9 tests OK; after Stage 1: see evidence log (27 tests OK) |
| `.\.venv\Scripts\python.exe scripts/verify_repo.py` | `Scan result : PASS` |
| `.\.venv\Scripts\python.exe cryptoshift_cli.py --help` | lists 9 subcommands incl. `data-summary`, `inventory` |
| `.\.venv\Scripts\python.exe cryptoshift_cli.py data-summary` | 320 rows / 5 dates / 0 dup keys; CESNET 25,000,000 rows; 100,000 rows in 4 chunks |
| `.\.venv\Scripts\python.exe cryptoshift_cli.py inventory` | 6 findings in demo nginx config |
| `.\.venv\Scripts\python.exe cryptoshift_cli.py scan` | 10 findings / 4 services (legacy scanner; prints absolute paths) |
| `.\.venv\Scripts\python.exe scripts/fetch_public_label_sources.py` | 5 sources, 15 files, 0 failures |
| `.\.venv\Scripts\python.exe scripts/evaluate_public_labels.py --split held_out` | TP 28 / FP 0 / FN 2 (not defensible size) |
| `openssl version` | not on PATH. Git's bundled `C:\Program Files\Git\usr\bin\openssl.exe` → OpenSSL 3.5.9, lists `X25519MLKEM768` |

## Commands intentionally NOT run

- `check-auth`, `demo`, `init-env`: create `.env` from `.env.example` if missing (`cli.py:init_local_env_file`).
- `evaluate`, `schedule`, `mvp-slice`: rewrite tracked files under `reports/`.
