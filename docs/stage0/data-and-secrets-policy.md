# Data and secrets policy

Dataset details: [`docs/data/DATASETS.md`](../data/DATASETS.md), [`data/registry.json`](../../data/registry.json).
Existing hygiene notes: [`docs/setup/project-structure.md`](../setup/project-structure.md) §4.

## Data

1. **Read-only inputs.** External datasets (CESNET-TLS22 S, banking PQC observations) and fetched public repos are
   never modified. Code opens them read-only.
2. **Paths via environment variables only:** `CRYPTOSHIFT_DATASET_DIR`, `CRYPTOSHIFT_CESNET_H5_PATH`,
   `CRYPTOSHIFT_PQC_OBS_CSV_PATH` (or the git-ignored `.cryptoshift_datasets.local.json`). No personal absolute
   paths in committed files (`scripts/verify_repo.py` checks for the local user path).
3. **No large or raw third-party data in Git.** `*.h5`, `*.hdf5`, `*.db`, `*.sqlite*` and `data/public/raw/` are
   git-ignored. Commit pointers, checksums, licences and small attributed snippets only.
4. **Derived output** goes to `scratch/derived/` (git-ignored).
5. **Labelling:** synthetic fixtures are always labelled SYNTHETIC and excluded from real-data metrics; CESNET is
   never used for detector precision/recall; ERROR rows stay unclassified.
6. **Scanning:** only repositories/systems the team owns or public open-source code fetched at a pinned commit. No
   live-bank or third-party network scanning.
7. **Attribution:** keep CC-BY-4.0 citations (CESNET-TLS22, PQ Readiness Index) and source licences for code labels.

## Secrets

1. Real keys live only in `.env` / `qcloud.env` (both git-ignored). Templates: `.env.example`, `qcloud.env.example`.
2. Never paste keys into chat, notebooks, screenshots, issues or commit messages.
3. **Rotate any key that was ever shared** in chat, a notebook output, a screenshot or a commit — treat it as
   compromised even if later deleted.
4. Tools must not print secrets: `redact_secrets()` (`optimization/auth_check.py`) and
   `inventory/common.redact_snippet()` mask keys, tokens, long key-like strings and user paths.
5. The inventory scanner never opens `.env*`, `qcloud.env`, `*.key`, `*.p12`, `*.pfx`, `*.jks`, `*.keystore`,
   `id_rsa*` (counted as "sensitive skipped"). A PEM with private key material is reported only as
   "private key material present", never parsed or echoed. Certificates yield algorithm, size, hash and expiry only.
6. Known pre-existing behaviour: `check-auth`, `demo` and `init-env` create `.env` from `.env.example` if missing;
   `resolve_dataset_paths()` and the QpiAI helpers load `.env`/`qcloud.env` into the process environment when the
   files exist (values are not printed).
7. Before every push: `scripts/verify_repo.py` must PASS, staging uses explicit paths only, and the staged diff is
   scanned for secret patterns (counts only reported).
