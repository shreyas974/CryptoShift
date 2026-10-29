# Labelling guidelines — cryptographic usage in public code and configs (v1)

Written **before** any public-code label was created. These are **team annotations**, not ground truth: one
annotator, second review pending (`reviewer: "pending"`).

## Unit of labelling

One label = **(file, line, algorithm family group)** inside a file listed in
`data/labels/public_code/sources.json`. Every line of a labelled file is in scope:

- a line with a label `positive` is a cryptographic usage we expect a detector to report;
- a line with a label `ambiguous` is excluded from precision and recall (reported separately);
- a line with a label `hard_negative` is an explicit trap (should **not** be reported);
- any other line of a labelled file is an implicit negative (a finding there counts as a false positive).

A line can carry several labels (e.g. one TLS cipher line enabling ECDHE, RSA authentication and 3DES).

## Family groups (matching key)

| Group | Includes |
|---|---|
| `RSA` | RSA keys, RSA-OAEP / PKCS#1 v1.5 encryption, RSA-PSS / PKCS#1 v1.5 signatures, static RSA key transport in TLS |
| `EC` | EC keys, ECDSA, ECDH/ECDHE, X25519/X448, Ed25519/Ed448 |
| `DH` | finite-field DH/DHE, ffdhe groups, dhparam |
| `DSA` | DSA |
| `LEGACY_SYM` | 3DES, DES, RC4, Blowfish |
| `WEAK_HASH` | MD5, SHA-1 used as a hash or signature digest |
| `TLS_PROTOCOL` | enabling SSLv2/SSLv3/TLS 1.0/TLS 1.1, or TLS 1.2 without TLS 1.3 |
| `PQC` | ML-KEM / ML-DSA / SLH-DSA / hybrid groups (informational; not part of vulnerability P/R) |
| `DEPENDENCY` | a manifest entry (requirements.txt, package.json, pom.xml) declaring a crypto-capable library; purpose `unknown` |
| `CERT_UNKNOWN` | a certificate is configured but its key algorithm cannot be seen from the file (always `ambiguous`) |

Multi-line statements are labelled once, at the line of the algorithm-identifying token, with a `span`
`[first_line, last_line]` covering the statement; a finding anywhere inside the span matches that label.

Purpose (`key_establishment`, `digital_signature`, `symmetric_encryption`, `message_digest`, `transport_protocol`,
`unknown`) is recorded per label and scored separately from detection.

## What counts as `positive`

1. A call, constructor or class reference that **performs or selects** a quantum-vulnerable or classically weak
   primitive: key generation/loading/construction of RSA/EC/DH/DSA keys, sign/verify/encrypt/decrypt/exchange,
   selecting a padding, curve, hash or cipher object (`padding.OAEP(...)`, `ec.ECDSA(...)`, `hashes.SHA1()`).
2. A configuration directive that **enables** such a primitive or protocol (`ssl_ciphers`, `ssl_protocols`,
   `ssl_ecdh_curve`, `SSLCipherSuite`, `SSLProtocol`, `CipherString`, `MinProtocol`, `ssl_dhparam`).
3. A literal algorithm identifier that selects an algorithm at that line (`algorithm="RS256"` in a JWT call,
   `hashlib.new("sha1")`).
4. Code in test files counts (it is real code), but is flagged as test code in reports.

## Hard negatives (must not be reported)

- `isinstance(...)` checks and type annotations naming key classes (they inspect, not use, a primitive).
- Imports on their own.
- Comments, docstrings, log/error strings and identifiers that merely mention an algorithm
  (`"RSA key is invalid"`, `def to_jwk_rsa`).
- HMAC/`HS256`, SHA-256/384/512, AES-GCM, ChaCha20, TLS 1.3 suites (not migration targets in this project).
- Look-alike names (`md5_total`, `rsa_report`, `ecosystem`).
- Configuration lines that are commented out or that only **disable** a primitive (`!3DES`, `-TLSv1`).

## Ambiguous

Use `ambiguous` when a reasonable reviewer could disagree whether the line is a usage, for example:

- an algorithm is chosen through a variable/dictionary lookup whose value is not visible at that line
  (`self.hash_alg()`, `ALGORITHMS[alg]`);
- a generic serialization/loading call that may return RSA, EC or other keys (`load_pem_public_key`);
- OpenSSL macro-only cipher strings (`HIGH:!aNULL`) whose effective suites depend on the build.

When purpose is unknown at the line, record `purpose: "unknown"` (the product must then HOLD for human review).

## Process rules

- Pin each repository to a commit SHA; record licence, file SHA-256 and line SHA-256 (of the stripped line).
- Copy short snippets only from permissively licensed sources (MIT/BSD/Apache-2.0) with attribution; otherwise
  store pointers and checksums only.
- Split **by repository**: `calibration` repositories may be used while developing detectors; `held_out`
  repositories are labelled before the detector is run on them and are never used to tune it.
- Labels must be written from reading the source, not copied from detector output.
- Record `annotator` and `reviewer` honestly; `reviewer: "pending"` until a second person reviews.
- CryptoAPI-Bench (Java) or other misuse benchmarks are separate and do not validate Python scanning.
