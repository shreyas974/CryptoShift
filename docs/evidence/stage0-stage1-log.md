# Stage 0 + Stage 1 evidence log

Chronological log of commands run while building Stage 0 (docs/claims) and Stage 1 (data, scanner baseline,
labelled set) on branch `feature/member-3-planning-verification`. Outputs are real and trimmed; local user
paths are shown as `~` and the repository root as `<repo>`. No secret values were read or printed.

Interpreter: `.\.venv\Scripts\python.exe` (Python 3.12.14). Shell: Windows PowerShell 5.1 and Git Bash.

---

## Phase 1 — Inspect (read-only)

### 1.1 Repository, branch, status, history, remote

```text
> git rev-parse --show-toplevel ; git branch --show-current
<repo>  (= ~/OneDrive/Documents/CryptoShift_Member3)
feature/member-3-planning-verification

> git status
Your branch is up to date with 'origin/feature/member-3-planning-verification'.
Changes not staged for commit:
	deleted:    docs/team/CryptoShift_Team_Roles_36h_and_Technical_Stack.docx
	deleted:    docs/team/CryptoShift_Team_Roles_and_Architecture.docx
Untracked files:
	notebooks/

> git log --oneline -10
5bcd3fd Skip CESNET streaming test when the dataset is not available locally
4474f85 Fix CESNET SHA-256 typo in datasets docstring
135256b Docs, dependencies and setup
f484cd5 CLI, reporting and UI entry (needs Member 4 review)
786f875 Scanner: config and AST detection, demo configs (needs Member 2 review)
b49117d Member 3: dataset loaders, MVP vertical slice, tests
2a1d7a2 Add role-based Git branch and collaboration workflow guide
527c6eb Document project structure, add team docs, and track prepared directory layout
e23c40e Reorganize CryptoShift into canonical src/ layout with PQC evaluation and verification docs
f0bdb52 Prepare CryptoShift project documentation and repository

> git remote -v
origin	https://github.com/shreyas974/CryptoShift.git (fetch)
origin	https://github.com/shreyas974/CryptoShift.git (push)
```

The two deleted DOCX files and `notebooks/` belong to the repo owner and were left untouched throughout.

### 1.2 Baseline tests and repo verifier (before any change)

```text
> .\.venv\Scripts\python.exe -m unittest discover -s tests -v
... 9 tests ...
Ran 9 tests in 2.774s
OK

> .\.venv\Scripts\python.exe scripts/verify_repo.py
Files inspected : 108
Scan result     : PASS (0 secret patterns, 0 forbidden files, 0 local user paths)
```

### 1.3 Secrets files (existence + ignore only; contents never opened)

```text
> ls .env qcloud.env
ls: cannot access '.env': No such file or directory
ls: cannot access 'qcloud.env': No such file or directory
> git check-ignore -v .env qcloud.env
.gitignore:7:.env	.env
.gitignore:11:qcloud.env	qcloud.env
```

Neither file exists in this checkout; both names are git-ignored.

### 1.4 Entry points and setup

- `cryptoshift_cli.py` → `src/cryptoshift/cli.py:main` (subcommands: `check-auth`, `init-env`, `schedule`,
  `evaluate`, `data-summary`, `scan`, `mvp-slice`, `demo`; no subcommand = `demo`).
- `pyproject.toml` console script `cryptoshift = cryptoshift.cli:main`; `requires-python = ">=3.10,<3.15"`.
- `src/cryptoshift/ui/app.py` (Streamlit UI, Member 4).
- `scripts/verify_repo.py` (hygiene/secret scan), `scripts/extract_bank_pqc_observations.py`.
- Installed in `.venv`: h5py 3.16.0, PyYAML 6.0.3, tables 3.11.1, numpy 2.5.4, pytest 9.2.0, streamlit 1.66.1,
  qpiai-opt 0.0.9, qpiai-quantum 0.3.0. `cryptography` was **not** installed at inspection time.

### 1.5 Dataset paths (names and sizes only; nothing loaded)

`CRYPTOSHIFT_DATASET_DIR`, `CRYPTOSHIFT_CESNET_H5_PATH`, `CRYPTOSHIFT_PQC_OBS_CSV_PATH` were all **unset** in the
shell, so `resolve_dataset_paths()` falls back to the default pack location
`~/.codex/.chatgpt-projects/<project>/output/cryptoshift_dataset` (exists).

```text
          839  ATTRIBUTION.txt
        2,391  manifest.json
        3,513  README.md
        1,049  verification.json
        2,489  verify_dataset.py
3,231,649,088  CESNET-TLS22/S/CESNET-TLS22-S.h5
       26,022  CESNET-TLS22/S/servicemap.csv
       35,992  pqc_evidence/banking_pqc_observations.csv
        3,380  pqc_evidence/prepare_pqc_evidence.py
        1,734  pqc_evidence/README.md
        1,431  pqc_evidence/summary.json
  ~26,300 x 5  pqc_evidence/raw/results_2026*.csv
        7,440  pqc_evidence/raw/targets.csv
```

### 1.6 Known issues observed

| Issue | Evidence |
|---|---|
| `check-auth` (and `demo`) call `init_local_env_file()`, which creates `.env` from `.env.example` if missing | `src/cryptoshift/cli.py:37-43,158,292`. Not run. |
| Broken README links to deleted DOCX | `README.md` and `docs/README.md` → `docs/team/CryptoShift_Team_Roles_36h_and_Technical_Stack.docx` (deleted in working tree, owner's change). `docs/setup/qpiai-shared-setup.md` **does exist** (tracked), so that link is fine. |
| `data/README.md` references files that do not exist | `data/public/README.md`, `data/public/processed/licma_real_misuse_findings.csv`, `data/labels/real_dataset_sources.json` — none present in the tree. |
| Python version mismatch | `pyproject.toml` allows `>=3.10`; project target is 3.11+. `.venv` is 3.12.14. |
| "13 findings across 6 services" is not a file scan | `scanner.scan_banking_services()` iterates the hard-coded dict `demo_bank_app/services.py:SYNTHETIC_BANK_SERVICES`; `line_number` is synthetic (`line_idx * 4`). |
| `data-summary` already exists but writes to a **tracked** folder | `cli.py:206-237` writes `reports/datasets/real_dataset_summary.{json,md}` (tracked). |
| No ignored output folder exists | `git check-ignore reports/datasets/x.json output/x data/derived/x` → nothing ignored. |

### 1.7 OpenSSL / Docker feasibility (nothing installed)

```text
> Get-Command openssl   -> openssl NOT on PATH
> Get-Command docker    -> docker NOT on PATH
> "C:\Program Files\Git\usr\bin\openssl.exe" version
OpenSSL 3.5.9 29 Sep 2026 (Library: OpenSSL 3.5.9 29 Sep 2026)
> ... list -kem-algorithms   (excerpt)
  X25519MLKEM768 @ default
  SecP256r1MLKEM768 @ default
  { 2.16.840.1.101.3.4.4.2, id-alg-ml-kem-768, ML-KEM-768, MLKEM768 } @ default
```

OpenSSL is not on PATH. The OpenSSL bundled with Git for Windows (3.5.9) is present and lists `X25519MLKEM768`,
so a local hybrid TLS 1.3 handshake trace is **feasible** in a later stage. No handshake was run in this stage.
Docker: PLANNED (not installed).

### 1.8 IDE

Antigravity IDE opened on the repo folder as a viewer only (`antigravity-ide.cmd <repo>`). Its UI (terminal
panes, its own agent) cannot be operated reliably from this session, so all commands below ran in the agent
shell, not inside the IDE.

---

## Phase 2 — Stage 0 docs and claim re-checks

Claims re-checked by calling the existing functions directly (no reports written; `demo`/`check-auth` not run):

```text
scan_banking_services: 13 findings, 6 services; evidence_type: Counter({'service_descriptor': 13})
file scan demo_bank_app/configs: 10 findings, 4 services: ['auth_gateway', 'card_vault', 'interbank_tls', 'payment_signing']
synthetic eval: 11 {'TP': 7, 'FP': 1, 'FN': 1, 'TN': 2} {'precision': 0.875, 'recall': 0.875}
fallback objective: 248.105 waves: {0: ['interbank_tls', 'ledger_audit'], 1: ['auth_gateway', 'payment_signing'], 2: ['card_vault', 'settlement_batch']}
gates passed: 6 / 6   (flags constant True unless wave0-not-ready or simulated failure)
protocol: MOCKED_PROTOCOL_TRACE (Real hashlib digests + NIST FIPS 203/204 specification byte sizes) 544 7661
```

Docs written: `docs/stage0/{scope,architecture-overview,requirements-traceability,demo-definition,setup,data-and-secrets-policy,claims-register}.md`.
README gained a short "Claim status" pointer to the claims register.

```text
> .\.venv\Scripts\python.exe cryptoshift_cli.py --help
... {check-auth,init-env,schedule,evaluate,data-summary,scan,inventory,mvp-slice,demo} ...   (exit 0)
> .\.venv\Scripts\python.exe cryptoshift_cli.py scan
Services Discovered : 4 (auth_gateway, card_vault, interbank_tls, payment_signing)
Findings Detected   : 10        (note: legacy scan prints absolute local paths to the console)
```

## Phase 3 — Datasets and `data-summary`

Pack metadata read (README.md, manifest.json, verification.json, ATTRIBUTION.txt, pqc_evidence/summary.json).
`verification.json` contains an absolute personal path; it was **not** copied into the repo.

```text
> sha256sum (small files only; the 3 GB HDF5 was not hashed)
2ac284d6...f69e46e  pqc_evidence/banking_pqc_observations.csv
f44913e0...a35b5    data/real/bank_tls_pqc_observations.csv
```

First h5py read failed: `OSError: Can't synchronously read data (can't open directory)`; dataset filter id
`32001` (Blosc, written by PyTables). Fix: install `hdf5plugin` in `.venv`.

```text
> .\.venv\Scripts\python.exe -m pip install hdf5plugin cryptography
Successfully installed cryptography-50.0.2 hdf5plugin-7.1.0

> .\.venv\Scripts\python.exe cryptoshift_cli.py data-summary
1. Banking PQC observations (REAL public TLS endpoints on given dates):
   - Rows                 : 320 across 5 scan dates (2026-04-23, 2026-05-10, 2026-09-03, 2026-09-14, 2026-10-02)
   - Duplicate keys       : 0 (key = (scan_file, host, ts); 64 unique hosts)
   - Status counts        : {'CLASSICAL': 80, 'ERROR': 65, 'PQ-SAFE': 175} (ERROR kept unclassified: 65)
2. CESNET-TLS22 S (REAL flow metadata; NOT bank data; NOT PQC ground truth):
   - File size            : 3,231,649,088 bytes (matches manifest: True)
   - Manifest SHA-256     : 36e3240b144bf8902e874e8fd875b6e7ac3e40b0706eb5f8d3f40720ff5a2e06 (not re-hashed in this run)
   - Tables / rows        : 14 tables | 25,000,000 rows | 20211004 to 20211017
   - h5py chunked scan    : 100,000 rows in 4 chunks (0.0847s, duplicate IDs in window=0)
Summary written (git-ignored): scratch\derived\data-summary\data_summary.{json,md}
> git check-ignore -v scratch/derived/data-summary/data_summary.json
.gitignore:19:scratch/	scratch/derived/data-summary/data_summary.json

> .\.venv\Scripts\python.exe -m unittest tests.test_data_summary -v
Ran 5 tests ... OK
```

Created: `data/registry.json`, `docs/data/DATASETS.md`, `src/cryptoshift/data_summary.py`, `tests/test_data_summary.py`.
Changed: `src/cryptoshift/cli.py` (`data-summary` now uses h5py and writes to `scratch/derived/`; `--out-dir` added).

## Phase 4 — Scanner baseline (additive, `src/cryptoshift/inventory/`)

```text
> .\.venv\Scripts\python.exe cryptoshift_cli.py inventory
Files seen        : 4 | by detector: {'tls_config': 1, 'python_ast': 1}
Findings          : 6 (vulnerable/weak 6, PQC/hybrid info 0)
  - [INV-0001] interbank_tls_nginx.conf:11 | ECDH | key_establishment | high | none
  - [INV-0002] interbank_tls_nginx.conf:12 | ECDH | key_establishment | medium | none
  - [INV-0003] interbank_tls_nginx.conf:12 | RSA | digital_signature | medium | none
  - [INV-0004] interbank_tls_nginx.conf:12 | RSA | key_establishment | medium | none
  - [INV-0005] interbank_tls_nginx.conf:12 | 3DES | symmetric_encryption | medium | none
  - [INV-0006] interbank_tls_nginx.conf:16 | RSA | digital_signature | low | none

> ... inventory --path data/fixtures/synthetic
Findings          : 1   (project_alpha_auth/token_digest.py:7 SHA-1)
```

The synthetic fixtures declare algorithms as string constants (e.g. `JWT_SIGNING_ALG = "RS256"`); the AST
detector intentionally ignores strings, so it reports far fewer findings there than the legacy regex scanner. The
detector was **not** tuned to the synthetic fixtures.

`tests/test_inventory.py`: first run 12/13 (openssl.cnf token `DEFAULT@SECLEVEL=2` not recognised as a macro);
fixed; 13/13 OK.

## Phase 5 — Labelling guidelines, public-code labels, metrics

Order followed: guidelines written; sources pinned and fetched; calibration labelled; detector tuned on calibration
only; detector frozen; held-out labelled (scanner not run on it); single held-out evaluation.

```text
> git ls-remote <repo> HEAD
jpadilla/pyjwt              16231abfd1d8eab4953e8779b3017b859c88565e   (MIT)          calibration
h5bp/server-configs-nginx   d2f2c3e2fac76f429adb738894499b8fb756d2f3   (MIT)          calibration
mpdavis/python-jose         018b310ddb8b50dcfd09a0c152117835a21dd656   (MIT)          held_out
certbot/certbot             0a97bd98b853c33e1e31d258006bca0048ba8226   (Apache-2.0)   held_out
h5bp/server-configs-apache  f9feb463fe136620ccde264b4cfbddfd8cd473b5   (MIT)          held_out

> .\.venv\Scripts\python.exe scripts/fetch_public_label_sources.py --print-checksums
... 15 files ... Sources: 5 | failures: 0
```

Licences confirmed from each checkout's LICENSE file. Clones live in `data/public/raw/` (git-ignored).

Calibration run 1 (before tuning): `TP=20 FP=22 FN=18`. The FPs were key classes used only as types (annotations,
`isinstance`, `Union[...]`, class tuples) plus double counting of one (line, group) unit. General fixes: skip
type-only references; add EC curve classes, `EllipticCurvePrivateNumbers`, `rsa_crt_*`,
`rsa_recover_prime_factors`; count one FP per (file, line, group).

```text
calibration run 2:  TP=31 FP=0 FN=7  P=1.0 R=0.8158 F1=0.8986   (tuned on this split; not a performance claim)
```

Detector frozen: `scratch/derived/detector_freeze.sha256` at 2026-10-29T06:07:18Z (python_ast.py `b092deca...`,
tls_config.py `7a5863d1...`, manifests.py `b9b56678...`). One scoring rule was then set **before** the held-out
run: dependency-manifest findings map to the `DEPENDENCY` group, as the guidelines already specified.

```text
> .\.venv\Scripts\python.exe scripts/evaluate_public_labels.py --split held_out
Status       : NOT YET MEASURABLE AT DEFENSIBLE SIZE (positives=30 < 100 or repos=3 < 3; single annotator)
Repos/files  : ['certbot', 'h5bp-apache', 'python-jose'] / 8 | labels {'positive': 30, 'ambiguous': 20, 'hard_negative': 28}
Counts       : TP=28 FP=0 FN=2
P / R / F1   : 1.0 / 0.9333 / 0.9655
Purpose (TP) : {'agree': 20, 'disagree': 2, 'finding_unknown': 6} | hard negatives triggered: 0
  FN certbot/.../options-ssl-apache.conf:7 DSA - DHE-DSS suites
  FN h5bp-apache/h5bp/tls/policy_strict.conf:29 EC - ECDHParameters X25519 (classical group)
```

(The status prints "repos=3 < 3" because the size test is an OR; the failing condition is positives < 100.)
The two held-out misses were **not** fixed afterwards, to keep the held-out result honest.

```text
> .\.venv\Scripts\python.exe cryptoshift_cli.py inventory --path data/public/raw/python-jose
Files seen : 4 | by detector: {'python_ast': 2, 'dependency_manifest': 1}
Findings   : 22 | By ambiguity: {'ambiguous': 12, 'none': 8, 'unknown': 2}
```

## Full suite and verifier after all changes

```text
> .\.venv\Scripts\python.exe -m unittest discover -s tests -v
Ran 27 tests ... OK
> .\.venv\Scripts\python.exe scripts/verify_repo.py
Scan result : FAIL (1 issue(s) detected)  - [private_key_pem_header] in tests/test_inventory.py
```

Cause: a literal PEM marker string in the redaction test (not key material). Fixed by building the string at
runtime, then re-run:

```text
Ran 27 tests ... OK
Files inspected : 136
Scan result     : PASS (0 secret patterns, 0 forbidden files, 0 local user paths)
```
