# Public-code labels (team annotations — not ground truth)

Line-level labels of cryptographic usage in **real, permissively licensed public repositories at pinned commits**,
used to measure the Stage 1 inventory detectors (`src/cryptoshift/inventory/`). Guidelines:
[`docs/data/labelling-guidelines.md`](../../../docs/data/labelling-guidelines.md) (written before labelling).

| File | Content |
|---|---|
| `sources.json` | repo URL, pinned commit SHA, licence, attribution, split, labelled files with SHA-256 |
| `labels_calibration.json` | 78 labels (38 positive, 20 ambiguous, 20 hard negative) — pyjwt, h5bp nginx |
| `labels_held_out.json` | 78 labels (30 positive, 20 ambiguous, 28 hard negative) — python-jose, certbot, h5bp apache |

Each label has: `source_id`, `file`, `line` (+ optional statement `span`), `label`, `family_group`, `purpose`,
`note`, `line_sha256`, a short snippet with attribution (MIT/Apache-2.0 sources only), `split`, `annotator`,
`reviewer`.

**Honesty notes**

- Annotator: one AI-assisted annotator (`claude-code`), which also wrote the detectors — a real bias risk.
  `reviewer` is `"pending"` for every label until a second team member reviews them.
- Third-party source trees are **not** committed. Fetch them at the pinned commits into the git-ignored
  `data/public/raw/` with `scripts/fetch_public_label_sources.py`, which also verifies file checksums.
- Split is by repository. The detector was tuned only on calibration repos; its source hashes were recorded in
  `scratch/derived/detector_freeze.sha256` (2026-10-29T06:07:18Z) before held-out labels were written, and the
  held-out split was evaluated once. One scoring-rule change (manifest findings map to the `DEPENDENCY` group,
  as the guidelines already specified) was made before that single held-out run.
- 30 held-out positives across 3 repositories is **not a defensible sample**; results are a sanity check only.
- These labels concern Python crypto-API usage and nginx/Apache TLS directives. They are unrelated to the synthetic
  fixture smoke test (`../synthetic_fixture_labels.json`) and to Java benchmarks such as CryptoAPI-Bench.

Reproduce:

```powershell
.\.venv\Scripts\python.exe scripts/fetch_public_label_sources.py
.\.venv\Scripts\python.exe scripts/evaluate_public_labels.py --split held_out
```

## Round 2 (added by Member 2, 2026-10-29; guidelines: `docs/data/labelling-guidelines-v2.md`)

- **Splits:**
  - The Stage 1 `held_out` repos (python-jose, certbot, h5bp-apache) are now `calibration-2`. Their results had been seen, and two detector fixes were made from them.
  - Their labels are unchanged; only the `split` value changed.
- **New labels, `labels_held_out_round2.json`:**
  - **Count:** 293 labels (155 positive, 62 ambiguous, 76 hard negative) on 16 files of 4 new held-out repos: nginx-proxy (MIT), mitmproxy (MIT), josepy (Apache-2.0) and spring-security (Apache-2.0).
  - **Provenance:** commits pinned; file SHA-256 recorded in `sources.json`; files fetched by `"fetch": "raw"`.
  - **Status:** `annotator: "AI-assisted (Claude) draft"`, `reviewer: "pending-human"`. These are not reviewed and not ground truth.
  - **Order of work:** detector and scoring sources were frozen first (`detector_freeze_round2.json`, 2026-10-29T10:43:28Z), then the labels were written, then the frozen detector was run once.
  - **Excluded:** `mitmproxy/certs.py` embeds a PEM private-key block (a publicly disclosed third-party CA key), so it was dropped before labelling.
- **Review:** `review_sheet.csv` lists every label (449 rows) with empty `reviewer`, `verdict` and `notes` columns. After filling it in, run `scripts/review_label_sheet.py --score` to get agreement, Cohen's kappa and recomputed metrics.
