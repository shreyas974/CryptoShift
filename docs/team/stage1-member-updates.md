# Stage 0 + Stage 1 — updates and actions per member

Source commit: `2860d9b` on `feature/member-3-planning-verification` (fast-forwarded into the member 1, 2 and 4
branches). Claim statuses: [`docs/stage0/claims-register.md`](../stage0/claims-register.md). Evidence:
[`docs/evidence/stage0-stage1-log.md`](../evidence/stage0-stage1-log.md).

## Everyone

- Pull your branch: `git switch <your-branch>` then `git pull`.
- Install the two new packages inside `.venv`: `.\.venv\Scripts\python.exe -m pip install hdf5plugin cryptography`.
- Check: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` (27 tests) and `scripts/verify_repo.py` (PASS).
- Shared files changed (please review): `src/cryptoshift/models.py` (7 optional `CryptoFinding` fields, all with
  defaults), `requirements.txt`, `pyproject.toml` (`hdf5plugin`, `cryptography`).
- Before pitching any number, check its status in the claims register (13 findings = synthetic descriptor;
  0.875/0.875 = synthetic smoke test; 544 B vs 7661 B and the 6/6 gates = mocked; QAOA −13.07 = not re-verified).

## Member 1 — docs, datasets, labels

Review (new files in your area):
- `docs/stage0/*` (7 docs), `docs/data/DATASETS.md`, `docs/data/labelling-guidelines.md`, `data/registry.json`.
- `data/labels/public_code/` — 156 labels on 5 pinned public repos. Every label has `reviewer: "pending"`:
  **a second-person review is the most useful next step** (start with `labels_held_out.json`, 78 labels).
- README gained one "Claim status" paragraph.

Open items:
- `data/README.md` references `data/public/README.md`, `data/public/processed/licma_real_misuse_findings.csv`,
  `data/labels/real_dataset_sources.json` — none exist. Fix or remove.
- `README.md` / `docs/README.md` link to the deleted `docs/team/CryptoShift_Team_Roles_36h_and_Technical_Stack.docx`.
- To reach a defensible metric: grow held-out positives from 30 to ≥100 across more repositories.

## Member 2 — discovery and inventory

Review:
- New package `src/cryptoshift/inventory/` (additive; `scanner.py` and `rules.py` untouched):
  `python_ast.py`, `tls_config.py`, `manifests.py`, `certificates.py`, `scan.py`, `report.py`, `common.py`.
- Tests: `tests/test_inventory.py` (13). Evaluation: `scripts/evaluate_public_labels.py`.

Known gaps (held-out misses, deliberately not tuned):
- DHE-DSS cipher suites are not mapped to DSA.
- Apache `SSLOpenSSLConfCmd ECDHParameters X25519` is not parsed (only `Groups`/`Curves`).
- Purpose often stays `unknown` (HOLD) for key generation/loading; data-flow analysis would help.
- The AST detector ignores string constants, so on `data/fixtures/synthetic/` it finds 1 item where the legacy
  regex scanner finds many — decide whether those fixtures should use real API calls.
- Legacy `scan` prints absolute local paths to the console.

## Member 3 — planning, verification, rollback (this branch)

- New: `src/cryptoshift/data_summary.py`, `tests/test_data_summary.py`, `scripts/fetch_public_label_sources.py`.
- Next (PLANNED): derive migration tasks from inventory findings instead of `demo_bank_app/services.py`;
  run a real hybrid TLS 1.3 handshake (Git-bundled OpenSSL 3.5.9 lists `X25519MLKEM768`) to replace the mocked
  trace and gates; measure overhead.

## Member 4 — full stack and CLI

Review `src/cryptoshift/cli.py`:
- `data-summary` now writes to `scratch/derived/data-summary/` (git-ignored) instead of the tracked
  `reports/datasets/`, reads CESNET with h5py, and has `--out-dir`.
- New `inventory` subcommand (`--path`, `--out-dir`) → `scratch/derived/inventory/inventory.cbom-like.json` + `.md`.
- The UI can consume the CBOM-like JSON; label it "CBOM-like", never "CycloneDX".
- Reminder: `check-auth`, `demo`, `init-env` create `.env` from `.env.example` if missing; `evaluate`, `schedule`,
  `mvp-slice` rewrite tracked `reports/` files.
