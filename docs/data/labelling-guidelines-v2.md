# Labelling guidelines v2 (round 2: new held-out repositories)

Written **before** any round-2 label was created (2026-10-29). v1 ([labelling-guidelines.md](labelling-guidelines.md))
still applies; this file lists only what changes.

## Status of the labels

- Every round-2 label is an **AI-assisted draft**: `annotator: "AI-assisted (Claude) draft"`, `reviewer: "pending-human"`.
  They are not reviewed and not ground truth. The same AI wrote the detectors (bias risk, see "Known biases").
- A teammate reviews them with `data/labels/public_code/review_sheet.csv` (one row per label: file, line, snippet,
  label, and empty `reviewer`, `verdict`, `notes` columns), then runs `scripts/review_label_sheet.py` to recompute
  metrics on the human-confirmed labels and report agreement.

## Splits (by repository)

| Split | Repositories | Use |
|---|---|---|
| `calibration` | pyjwt, h5bp-nginx | detector development (unchanged) |
| `calibration-2` | python-jose, certbot, h5bp-apache | **formerly held-out.** Their results were seen in Stage 1, so they may now be used for fixes. Two fixes were made from them: DHE-DSS cipher suites -> DSA signature; Apache `SSLOpenSSLConfCmd ECDHParameters` -> key-exchange groups. Effect recorded in `docs/member2/README.md`. |
| `held_out` (round 2) | new repositories listed in `sources.json` with `"round": 2` | labelled before the detector is run on them; detector sources frozen (hash recorded) before labelling; run once; never used for tuning |

## Choosing round-2 repositories

- Permissive licence confirmed from the repository's own LICENSE file at the pinned commit (MIT, BSD-2/3-Clause,
  Apache-2.0). Record licence, URL, commit SHA and SHA-256 of every labelled file.
- Realistic mix: Python crypto code, TLS server configuration, dependency manifests, and Java (the Java detector is
  limited in scope; Java positives it cannot see are still labelled, so its recall is measured honestly).
- Files are chosen for **cryptographic relevance read from the source**, never because of what a detector reports.
- Third-party files are fetched into git-ignored `data/public/raw/` by `scripts/fetch_public_label_sources.py`;
  only pointers, checksums and short attributed snippets (permissive licences only) are committed.

## Changes to the unit and the groups

- New family groups: `ECB_MODE` (AES or another block cipher in ECB mode, including JCA `"AES"` without a mode, whose
  provider default is ECB), `KEYSTORE` (JKS/JCEKS key store type; always `ambiguous`, contents unknown).
  `MD4`/`MD2` join `WEAK_HASH`; `RC2` joins `LEGACY_SYM`.
- A **Java string literal that names an algorithm and is passed to a JCA factory** (`Cipher.getInstance("RSA/ECB/...")`,
  `Signature.getInstance("SHA256withRSA")`) is `positive` at the call line. A Java enum or constructor argument naming an
  algorithm (`RS256("SHA256withRSA")`) is `positive` too (it selects an algorithm), even though the limited Java
  detector cannot see it. A call whose algorithm arrives through a variable is `ambiguous`.
- An **algorithm constant** (`ALG = "RS256"`) is `positive` only if it is used to select an algorithm in that file;
  otherwise `ambiguous`.
- **Templated configs** (e.g. Go/Jinja templates producing nginx config): a directive line is labelled like a normal
  directive. A directive whose value is a template expression is `ambiguous`.
- Shell/Dockerfile: an `openssl` / `ssh-keygen` command that generates or selects a vulnerable key or algorithm is
  `positive`; `echo`, comments, installs and `openssl version` are negatives.
- A manifest entry that declares a crypto-capable library (`cryptography`, `pyOpenSSL`, `bcprov`, `nimbus-jose-jwt`)
  is `positive` with group `DEPENDENCY` and purpose `unknown`.

## Known biases (stated up front)

1. The annotator also wrote the detectors and knows their rules; labels may unconsciously follow detector logic.
2. One annotator; no agreement statistic exists until the review sheet is filled in.
3. File selection favours crypto-dense files, so precision on ordinary application code may be lower.
