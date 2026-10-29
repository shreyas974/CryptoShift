# CryptoShift — Real Dataset Summary, Provenance, and Streaming Audit

## 1. PQ Readiness Index — Banking Sector Longitudinal TLS 1.3 Observations

- **Status:** `verified`
- **Attribution:** Nguyen Dong, Global PQ Readiness Index (2026), https://github.com/xuxu298/PQReadinessIndex
- **License:** `CC-BY-4.0`
- **Total Observations:** `320` across `5` scan dates (`2026-04-23, 2026-05-10, 2026-09-03, 2026-09-14, 2026-10-02`)
- **Duplicate Observation Key Check (`(scan_file, host, ts)`):** `0` duplicates (`320` unique keys; `64` hosts measured longitudinally across dates)
- **Overall Status Counts (Unchanged from Source):** `{"ERROR": 65, "PQ-SAFE": 175, "CLASSICAL": 80}` (`ERROR` kept strictly unclassified: `65`)

### Per-Scan-Date Status Breakdown

| Scan Date | PQ-SAFE (`X25519MLKEM768`) | CLASSICAL (`X25519`) | ERROR (Unclassified) | Total |
|---|---:|---:|---:|---:|
| `2026-04-23` | `14` | `36` | `14` | `64` |
| `2026-05-10` | `15` | `35` | `14` | `64` |
| `2026-09-03` | `48` | `3` | `13` | `64` |
| `2026-09-14` | `49` | `3` | `12` | `64` |
| `2026-10-02` | `49` | `3` | `12` | `64` |

### Caveats & Scope Boundaries (PQ Readiness Index)

- Each row records a single public TLS 1.3 endpoint handshake observation on a specific scan date.
- Status values ('PQ-SAFE', 'CLASSICAL', 'ERROR') are preserved unchanged from the source scan files.
- 'ERROR' rows are unclassified probe outcomes (e.g., server alert or DNS failure) and are NEVER relabelled as 'CLASSICAL' or PQC-negative.
- Repeating host IDs (h101..h164) across the 5 scan dates are valid longitudinal measurements; duplicate checking uses (scan_file, host, ts) and confirmed 0 duplicates.
- These public-edge TLS key-establishment observations do NOT reveal a bank's internal software estate, ML-DSA digital signature adoption, internal service dependencies, or overall migration status.

---

## 2. CESNET-TLS22 Provider-Defined `S` Subset (Real TLS Flow Metadata)

- **Status:** `verified`
- **Required Citation:** Jan Luxemburk and Tomáš Čejka, 'Fine-grained TLS services classification with reject option,' Computer Networks, vol. 220, 2023, article 109467, https://doi.org/10.1016/j.comnet.2022.109467
- **DOI & Source:** `10.5281/zenodo.10610895` (<https://zenodo.org/records/10610895>)
- **License:** `CC-BY-4.0`
- **Collection Period:** 2021-10-04 through 2021-10-17 (CESNET2 network)
- **File Size:** `3,231,649,088` bytes (`3.23 GB` decimal; matches expected: `True`)
- **Recorded SHA-256:** `36e3240b144bf8902e874e8fd875b6e7ac3e40b0706eb5f8d3f40720ff5a2e06`
- **Total Daily Tables:** `14` tables (`/flows/D20211004` .. `/flows/D20211017`)
- **Total Flow Rows:** `25,000,000` (`0` duplicate flow IDs in 25M full audit)
- **Incremental Streaming Benchmark:** Streamed `50,000` rows in `2` chunks (`chunk_size=25,000`) in `0.3399s` (`147,115.2` rows/sec; `0` duplicate IDs in streamed window)
- **Top Categories in Streamed Window:** `{"Other services and APIs": 7691, "Social": 5330, "Streaming media": 4996, "Analytics & Telemetry": 3912, "Antivirus": 3459, "Advertising": 3268, "File sharing": 3109, "Software updates": 3037, "Music": 2685, "Videoconferencing": 2538}`

### Prohibited Interpretations (CESNET-TLS22-S)

- NOT bank-internal source code, configuration, or network infrastructure data.
- NOT PQC adoption or migration ground truth (captured in Oct 2021 before PQC endpoint transition).
- APP and CATEGORY labels identify application services, NOT cryptographic algorithms or PQC posture.
- NEVER use CESNET-TLS22 service labels to compute PQC detector precision or recall.

---

## 3. Detector Evaluation Separation Policy

- CESNET service labels are never used for PQC detector precision/recall.
