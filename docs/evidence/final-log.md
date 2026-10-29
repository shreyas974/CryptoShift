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

## Phase C: Member 3 (base worktree, branch `feature/member-3-planning-verification`)

| Step | Command | Result |
|---|---|---|
| C0 merge | `git merge --no-ff feature/member-2-discovery` (local) | merge commit `c8340fa`; no conflicts; uncommitted Member 3 work untouched; 79 tests OK (1 skipped) |
| C2 graph | `planning.dependency_graph.member2_observed_edges` + `findings.collect_findings` on Member 2 attribution | demo bank: 4 OBSERVED (file+line), 5 DECLARED, 0 cycles, 0 unknown; fixture: 9 OBSERVED, 3 unknown. Defect found by a new test and fixed: legacy file-stem service names (`nginx`, `docker-compose`) had hidden Member 2 edges |
| C2 test change | `tests/test_member3_planning.py` | unknown endpoint now keeps the full host (`partner-bank.example`); expectation updated, reason recorded in the test |
| C4 plan | `scripts/member3_pipeline.py` | objective 299.1 (was 292.8, more findings from Member 2 detectors); auth_gateway now PROPOSED (unknown-purpose RSA finding) |
| C8 docs read | WebFetch docs.sarvam.ai (llms.txt, authentication, pricing, rate limits, chat-completions v1) | endpoint `/v1/chat/completions`, header `api-subscription-key`; models only `sarvam-105b`, `sarvam-105b-conversations` (sarvam-30b not accepted); Rs 15/M in, Rs 60/M out excl. GST; 60 rpm; 402 = credits exhausted |
| C8 tests | `tests/test_member3_sarvam.py` (fake HTTP transport) | validator rejects forced bad answers (fake approval, wrong ID, role swap, secret); fallback on no key / no budget / policy / 429 / 402; key only in header |
| C8 preview | `scripts/evaluate_agent.py --preview` | 11 of 24 questions would reach the cloud; estimate Rs 0.20 typical, Rs 0.73 worst case |
| `.env` | created by Claude from `.env.example` (blank) at the owner's request; owner filled keys | Claude never opened it; only booleans checked (SARVAM, QPIAI_OPT, QPIAI_QCLOUD set) |
| C8 live run (owner-approved) | `scripts/evaluate_agent.py --mode sarvam --max-spend-inr 0.75` (no balance stated, hard cap used) | 17 requests, 8,701 prompt + 2,013 completion tokens, est. Rs 0.251; 8 SARVAM_CLOUD / 16 TEMPLATE_FALLBACK; v2 24/24; v3 (added after the run, applied offline to the same answers) 18/24; 6 cloud answers "unknown" despite evidence; 3 validator double-rejections (false alarms that failed safe) |
| C4 QpiAI (owner-approved) | `scripts/member3_phase3.py --authorize-local-solve` | `solve(mode="local")`: optimal, execution_mode local, objective 299.1 = baseline 299.1, same assignment, solver 0.044 s; QAOA P(opt) 0.085 vs 0.0625 |
| key leak check | scan of 285 output/report/code files for any `.env` value (count only) | 0 files |
| C7 triage | `scripts/member3_phase5.py` | 79 rows / 8 repos; model macro-F1 0.273 vs rules 0.783: rules kept |
| C1 notebooks | rename 09 -> `09_assistant_demo`; `build_member3_notebooks.py`; `jupyter nbconvert --execute` x10 to `scratch/derived/executed/` | first pass: 08 failed (round-2 label sources not fetched) -> fetched (9 sources, 0 failures) -> all 10 exit 0, 0 errors, 19 charts; tracked copies outputs cleared |
| C9 contract | `scripts/build_member3_contract.py` | 4/4 examples validate (agent API now requires `mode`) |
