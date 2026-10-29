# Member 2: discovery and inventory (v1.1)

Status labels follow `docs/stage0/claims-register.md`. Every number below was produced by a command recorded in
`docs/evidence/final-log.md`. Static analysis only: an inventory is never "complete".

## What the scan path is now

| Path | Role |
|---|---|
| `src/cryptoshift/inventory/` (`cryptoshift_cli.py inventory`, `scripts/inventory_v11.py`) | **Main scan path.** Detectors resolve imports, keys and directives; findings carry file, line, purpose, ambiguity, service attribution and a redacted snippet. |
| `src/cryptoshift/scanner.py` (`cryptoshift_cli.py scan`) | Legacy regex scanner, kept for the synthetic service descriptors (`demo_bank_app/`). Its console output now prints repo-relative (or scan-root-relative) paths, never absolute local paths. |

### Legacy vs new results (documented difference)

- The legacy scanner matches text patterns, including string constants such as `JWT_SIGNING_ALG = "RS256"`.
- The Stage 1 AST detector ignored string constants, so it found 1 item on `data/fixtures/synthetic/`.
- **Decision:** add a *scoped* "algorithm constant" rule. It fires only when all of these hold:
  - the assignment is at module or class level (`NAME = "literal"`);
  - `NAME` is UPPER_CASE and contains an algorithm keyword (ALG, CIPHER, SCHEME, KEX, KEM, SIGNING, SIGNATURE, WRAP, HASH, DIGEST, CURVE, GROUP, PADDING, JWS, JWE);
  - the value is an *exact* identifier from a closed vocabulary (`inventory/algorithm_ids.py`).

  Confidence is always `low`, because the constant may never be used.
- **Hard-negative tests:** HMAC names, free text (`"RS256 not supported"`), lower-case names, names without a keyword, function locals and comments.
- **Measured effect:**

  | Set | Before | After |
  |---|---|---|
  | Synthetic fixtures | 1 finding | 10 findings (7 vulnerable constants + 1 `hashlib.sha1` call + 2 PQC info) |
  | Calibration | P 1.0, R 0.816 | unchanged |
  | Stage 1 held-out | P 1.0, R 0.933 | unchanged |

## Service attribution (`inventory/services.py`)

Rules apply in order; the first match wins. Every finding carries `service_id`, `service_id_basis` and `service_id_confidence`.

1. **declared**: the file declares itself. Recognised forms: `service_id:` key, `SERVICE_ID = "..."`, `spring.application.name=`, or a `Service ID: x` header comment. Confidence is high (medium for the comment form).
2. **compose**: the file is inside a docker-compose service's build context or volume mount. Confidence high.
3. **folder**: the nearest folder with a service marker (Dockerfile, pyproject.toml, setup.py, package.json, pom.xml, build.gradle, go.mod), or a child of `services/`, `apps/` or `microservices/`. Confidence medium.
4. **file_name**: a non-generic config file name (`payments_tls.conf` → `payments_tls`). Confidence low.
5. **unknown**: nothing matched. The id stays `unknown` (confidence `none`) and is never guessed.

## Detectors added in v1.1 (each with unit tests and hard negatives)

| Detector | Files | Covers |
|---|---|---|
| `structured_config` | `.yaml/.yml` (PyYAML compose marks for lines), `.properties`, `java.security`, `.json` | crypto-keyword keys only (cipher, protocol, group, curve, algorithm, signature, digest, ...). Never reports values under disabling keys (`disabled`, `exclude`, `deny`, ...). Checks `jdk.tls.disabledAlgorithms` for gaps. Protocol lists are judged as a whole. |
| `haproxy` | `haproxy*.cfg`, `.cfg` with HAProxy sections | `ssl-default-bind/server-ciphers/curves/options`, `bind`/`server` options (`ciphers`, `curves`, `ssl-min-ver`, `ssl-max-ver`, `no-tlsv13`, `force-*`, `crt`), DH params |
| `shell_script` | `.sh/.bash/...`, `Dockerfile*` | `openssl genrsa/req -newkey/genpkey/ecparam/dhparam/gendsa/dgst/enc/rsautl/s_client`, `ssh-keygen -t`. Only when openssl/ssh-keygen is the command word (`echo`, comments and installs ignored). Passphrases, `pass:` values and key/output paths are masked. |
| `java_source` | `.java` | **Java detector with limited scope.** See the scope notes below. |

**Java detector scope.**
- **What it handles:**
  - Tokenising is comment- and string-aware.
  - JCA classes resolve through imports (or fully qualified names); a same-named local class shadows them.
  - Covered calls: `Cipher`, `KeyPairGenerator`, `Signature`, `KeyAgreement`, `MessageDigest`, `SSLContext`, `KeyStore` `.getInstance(...)`, where the argument is a literal or a String constant assigned once in the same file.
- **What it does not handle:**
  - data flow across methods or files, enums, `KeyFactory`/`KeySpec`;
  - the Bouncy Castle lightweight API;
  - Kotlin.

Also new in v1.1:
- **Fixes from calibration-2** (from the Stage 1 held-out misses): DHE-DSS cipher suites now map to a DSA signature; Apache `SSLOpenSSLConfCmd ECDHParameters` is now parsed as key-exchange groups.
- **Redaction:** long tokens are masked unless they have the exact shape of an IANA suite or JCA name. Before this fix, `RSA/ECB/OAEPWith...Padding` was wrongly masked as a secret.

## Relationship evidence (`inventory/relationships.py`, schema `schemas/relationships.schema.json`)

- **Edge sources (OBSERVED only, each with file, line, kind, confidence and a ≤160-char redacted snippet):**
  - nginx `proxy_pass` and `upstream` servers;
  - HAProxy backend `server` lines;
  - compose `depends_on` / `links`;
  - URLs and host-valued keys in configs;
  - explicit `depends_on` lists in service configs;
  - Python imports of another service's package.
- **No invented edges:** a reference that matches no known service goes to `unknown_references` instead. Loopback and self references are ignored.
- **Example:** `schemas/examples/relationships.example.json`, from a real run on the SYNTHETIC fixture `tests/fixtures/multiservice_bank`. It has 9 edges and 3 unknown references.

## Output v1.1

- **CBOM-like JSON (`cryptoshift-cbom-like/1.1`, schema `schemas/inventory-cbom-like-1.1.schema.json`):**
  - adds service attribution, the service catalogue and relationships;
  - adds detector versions, scan start/end time, and the SHA-256 of every parsed input file plus an input-set hash.
- **Markdown report:** same content in readable form.
- **Optional CycloneDX 1.6 subset** (`inventory/cyclonedx.py`, `scripts/inventory_v11.py --cyclonedx`):
  - Contents: cryptographic-asset components with evidence occurrences (file, line), application components per service, and dependencies from the edges.
  - Schema source: the official CycloneDX schema from github.com/CycloneDX/specification, tag 1.6.1, commit `8a27bfd1be5b`, Apache-2.0. `scripts/fetch_cyclonedx_schema.py` fetches it and checks the SHA-256 of `bom-1.6`, `spdx` and `jsf`.
  - Result: the multiservice fixture and `demo_bank_app/configs` outputs both **validated against CycloneDX 1.6 schema, subset**.
  - Validator check: a deliberately broken copy fails, so the validator is active.
  - Even a schema-valid subset is **not a complete inventory**.

## Detection results by set (all labels are AI-assisted drafts; human review pending)

| Set | Repos / files | Positives | TP | FP | FN | Precision | Recall | Status |
|---|---|---|---|---|---|---|---|---|
| Synthetic smoke test (`data/fixtures/synthetic`) | 3 folders | (not line-labelled for this scorer) | – | – | – | – | – | SYNTHETIC; 10 findings, decoy ignored; not a metric |
| Calibration (pyjwt, h5bp-nginx) | 2 / 7 | 38 | 31 | 0 | 7 | 1.0 | 0.816 | used for development |
| Calibration-2 (python-jose, certbot, h5bp-apache) | 3 / 8 | 30 | 30 | 0 | 0 | 1.0 | 1.0 | **seen data**: was held-out in Stage 1 (0.933); the two misses were fixed from it, so this is not a held-out claim |
| **Held-out round 2** (nginx-proxy, mitmproxy, josepy, spring-security) | 4 / 16 | 155 | 18 | 0 | 137 | 1.0 | **0.116** | labelled before the run; detector frozen 2026-10-29T10:43:28Z; run once; no tuning |
| CryptoAPI-Bench mapped subset (Java) | 1 benchmark / 65 cases | 51 insecure cases | 22 | 9 | 29 | 0.71 | 0.43 | separate; see `cryptoapi-bench.md` |

**Why held-out recall is low.** This is the honest result. The misses are coverage gaps, not wrong findings (0 FP, 0 hard negatives triggered):

| Gap | Missed positives |
|---|---|
| nginx-proxy's `nginx.tmpl` (a Go template) is never parsed, because `.tmpl` is not a dispatched suffix | 65 |
| Cipher-suite strings inside a Python tuple (`_DEFAULT_CIPHERS`) are not analysed | 39 |
| JWS algorithm names passed to constructors (`_JWARS("RS256", ...)`) and Java enum constants (`RS256(...)`) are not detected | 20 |
| `KeyFactory` / `KeySpec` are outside the Java scope | 7 |
| `pyproject.toml` dependency tables are not parsed | 3 |
| The pyOpenSSL `set_tmp_ecdh` / `SSL_CTX_set_tmp_dh` calls are not covered | 2 |

The first two gaps alone account for 104 of the 137 misses, so the per-file concentration is high.

Other notes on this run:
- **Purpose:** agreement on the 18 TPs was 4 agree and 14 where the finding says `unknown` (HOLD).
- **Excluded file:** `mitmproxy/certs.py` was dropped before labelling because it embeds a PEM private-key block. That key is a publicly disclosed, already-compromised third-party CA key, but the project's rule is never to handle key material.

## Limits

- Static analysis only. There is no data flow beyond same-file constants (Java) and call-site context (Python padding).
- Cipher-string findings depend on the OpenSSL build and on the peers.
- Labels are AI-assisted drafts by the same AI that wrote the detectors (a bias risk). `reviewer` is `pending-human`. Use `data/labels/public_code/review_sheet.csv` and `scripts/review_label_sheet.py --score`.
- Never claim: "complete inventory", "validated detector", "ground truth", or "CycloneDX compliant" (say "validated against CycloneDX 1.6 schema, subset").
