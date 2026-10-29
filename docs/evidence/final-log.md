# Final run evidence log (Members 2, 3, 4)

Every command run for the final phases with its real, redacted result. Paths are repo-relative. Secrets are never
printed; `.env` / `qcloud.env` were only checked for existence and git-ignore status.

## Phase A: inspection (2026-10-29, read-only, base worktree `CryptoShift_Member3`)

| Command | Result |
|---|---|
| `git branch --show-current` / `git log --oneline -5` | `feature/member-3-planning-verification` @ `eea1f15` (eea1f15, 7c30880, 7d006fd, b021140, 35abf5b) |
| `git fetch origin`; `git log --oneline origin/<branch> ^fa4a15b` | member-2-discovery, member-4-fullstack, member-1-docs-data-bloq: **no commits** after fa4a15b; member-3: the 5 own commits above; `main` and `chore/restructure`: none |
| `git worktree list` | `CryptoShift` (original, not touched) and `CryptoShift_Member3` |
| tool versions | Python 3.12.14, pip 26.2.2, git 2.56.0, Git's OpenSSL 3.5.9; Docker not installed; RAM 15.7 GB; i5-11400H |
| `.env`, `qcloud.env` | neither exists; both git-ignored (not read) |
| `openssl list -kem-algorithms / -signature-algorithms / -tls1_3 -tls-groups` | ML-KEM-512/768/1024; ML-DSA-44/65/87, SLH-DSA; groups include X25519MLKEM768, SecP256r1MLKEM768 |
| `cryptography` 50.0.2 | modules `mlkem` (MLKEM768/1024) and `mldsa` (MLDSA44/65/87) present |
| `python -m unittest discover -s tests` | 53 tests OK |
| `scripts/verify_repo.py` | PASS (191 files, 0 secret patterns) |

## Phase B: Member 2 (worktree `CryptoShift_Member2`, branch `feature/member-2-discovery`)

| Step | Command | Result |
|---|---|---|
| worktree (approved) | `git worktree add ..\CryptoShift_Member2 feature/member-2-discovery`; `git merge --ff-only origin/feature/member-2-discovery` | at `fa4a15b`, clean |
| venv | `python -m venv .venv`; `pip install -r requirements.txt pyyaml jsonschema`; `pip check` | no broken requirements; 27 tests OK |
| baseline before changes | `scripts/evaluate_public_labels.py --split calibration` / `--split held_out` | calibration TP 31 FP 0 FN 7 (P 1.0 R 0.8158); Stage 1 held-out TP 28 FP 0 FN 2 (P 1.0 R 0.9333) |
| B1 legacy console | `cryptoshift_cli.py scan --path <absolute path>` | prints `data/fixtures/synthetic/...` (repo-relative); outside the repo it prints scan-root-relative paths |
| B1 constant rule effect | `scan_inventory(data/fixtures/synthetic)` | 10 findings (was 1); calibration and held-out metrics unchanged |
| B3/B4 fixture run | `scan_inventory(tests/fixtures/multiservice_bank)` | 45 findings; 9 OBSERVED edges; 3 unknown references; all hard negatives silent. Two defects found and fixed: (1) over-redaction of JCA/IANA names, (2) YAML protocol list judged per item |
| calibration-2 fixes | re-run both splits | calibration unchanged; former held-out (now calibration-2) TP 30 FP 0 FN 0. Seen data, not a held-out claim |
| B5 schema fetch | `scripts/fetch_cyclonedx_schema.py` | bom-1.6 `efc54d74…`, spdx `c4191719…`, jsf `8bae002c…` OK (tag 1.6.1, commit 8a27bfd1be5b, Apache-2.0) |
| B5 CycloneDX | `scripts/inventory_v11.py --path tests/fixtures/multiservice_bank --cyclonedx` (and `demo_bank_app/configs`) | both "validated against CycloneDX 1.6 schema, subset" (0 errors); negative control with an invalid enum: 1 error |
| B6 freeze | `scripts/evaluate_public_labels.py --freeze` | 18 detector/scoring files frozen at 2026-10-29T10:43:28Z |
| B6 sources | `git ls-remote` + LICENSE read at pinned commits | nginx-proxy MIT `bff2cdd`; mitmproxy MIT `df14a28`; josepy Apache-2.0 `7069e07`; spring-security Apache-2.0 `f97bd24` |
| B6 safety stop | reading `mitmproxy/certs.py` | file embeds a PEM private-key block (publicly disclosed, already-compromised third-party CA key, not ours; nothing to rotate). Not copied or printed; file deleted locally and excluded from the label set; PEM-block check on all other fetched files: none |
| B6 labels | hand-written from reading the files; `--fill` | 293 labels (155 P / 62 A / 76 H) on 16 files; snippets checked: 0 contain key material |
| B6 held-out run | first executed by `scripts/review_label_sheet.py --score` (dry run, which scores all splits); then `scripts/evaluate_public_labels.py --split held_out` | freeze **MATCH**; TP 18, FP 0, FN 137; P 1.0, R 0.1161, F1 0.2081; per source josepy 15/12, mitmproxy 0/43, nginx-proxy 2/65, spring-security 1/17 (TP/FN); 0 hard negatives triggered. Not tuned afterwards |
| B6 review sheet | `scripts/review_label_sheet.py --make` | 449 rows, 0 reviewed |
| B7 source | `git clone --filter=blob:none` CryptoAPI-Bench @ `e6b6b50` | MIT (LICENSE read); 203 java files; labels in `CryptoAPI-Bench_details.xlsx` (182 rows; 18 line cells corrupted into dates by Excel) |
| B7 run 1 | `scripts/evaluate_cryptoapi_bench.py` | 57 cases; TP 21 FP 9 FN 24 (harness bug: names without `.java` and multi-file cells not resolved) |
| B7 run 2 | same, after the name-resolution fix only | 65 cases; TP 22 FP 9 FN 29 TN 4; P 0.7097 R 0.4314 |
