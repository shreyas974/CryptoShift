# CryptoAPI-Bench: mapped-subset evaluation of the Java detector

> This checks recognition of known Java API patterns; it is not a banking dataset and does not validate Python scanning.

**Source**

| Item | Value |
|---|---|
| Repository | https://github.com/CryptoAPI-Bench/CryptoAPI-Bench |
| Licence | MIT, Copyright (c) 2018 Sharmin Afrose (LICENSE file confirmed) |
| Commit | `e6b6b50fef6970151300c1ac2de62e188ba6de19` |
| Local copy | Blob-less clone in git-ignored `data/public/raw/cryptoapi-bench/`. It is never built or executed. |
| Checksums | `CryptoAPI-Bench_details.xlsx` sha256 `8589f958cb2cb9dd…` (full value in `scratch/derived/cryptoapi-bench/cryptoapi_bench_eval.json`), plus a manifest hash over all 203 `.java` files |

## What its labels are

- The spreadsheet marks each case file as an insecure or secure (`Vulnerability Exists? = True/False`) **crypto-API misuse**.
- Each row has a "Type of Vulnerability" and line numbers.
- The cases cover 16 misuse categories, such as broken ciphers, broken hashes, ECB, static keys/IVs/salts, PBE iterations, predictable seeds, dummy trust managers and HTTP.
- These are **not quantum-vulnerability labels**.

## Explicit mapping (decided before scoring)

| Benchmark type | Detector group | Note |
|---|---|---|
| DES / Blowfish / RC4 / RC2 used | `LEGACY_SYM` | mapped |
| MD5 / SHA1 / MD4 / MD2 used | `WEAK_HASH` | mapped |
| Usage of ECB | `ECB_MODE` | mapped |
| RSA keysize 1024 bits | `RSA` | **partial**: the detector reports RSA use but does not check key size. Secure 2048-bit cases are not counted as FP, because for PQC every RSA key is in scope (1 such case was flagged and is reported separately). |
| IDEA, HmacMD5, HmacSHA1, static key/IV/salt/password, PBE iterations, seeds, credentials, HTTP, dummy certificate/hostname verifiers, socket hostname, PRNG | – | **unmapped, not scored** |

## Unit and rules

**Unit:** one benchmark case, i.e. one spreadsheet row.
- **Insecure case:** TP if the detector reports the mapped group on a listed line; otherwise FN.
- **Secure case:** FP if the detector reports that group anywhere in the case file; otherwise TN.

**Exclusions:**
- 8 rows whose line-number cell Excel had turned into a date are excluded.
- 2 rows reference files that do not exist.

## Results (detector `java_source/1.0`, frozen with the other detectors)

| Group | TP | FP | FN | TN | Precision | Recall |
|---|---|---|---|---|---|---|
| LEGACY_SYM | 12 | 4 | 8 | 2 | 0.75 | 0.60 |
| WEAK_HASH | 8 | 4 | 12 | 1 | 0.67 | 0.40 |
| ECB_MODE | 1 | 1 | 5 | 1 | 0.50 | 0.17 |
| RSA (partial) | 1 | 0 | 4 | 0 | 1.00 | 0.20 |
| **Overall (65 cases)** | **22** | **9** | **29** | **4** | **0.71** | **0.43** |

**Run history.** Two runs, both recorded:
- **Run 1:** scored 57 cases (TP 21, FP 9, FN 24). It had a harness bug: spreadsheet names without `.java`, and multi-file cells, were not resolved.
- **Run 2:** after fixing name resolution only (detector and scoring rules unchanged) it scored the 65 cases above.

## Why it misses and over-reports

- **False positives:** they come from the benchmark's *path-sensitive* "secure" variants. The insecure literal is present but on a path that never runs, and the detector has no path sensitivity.
- **False negatives:**
  - *Interprocedural* cases, where the algorithm arrives through a parameter or field set in another method;
  - *multi-class* cases;
  - `Cipher.getInstance("AES")` without a mode is reported as `AES-ECB` with medium confidence, but the benchmark's ECB rows point at other lines.

None of this was tuned after the run.
