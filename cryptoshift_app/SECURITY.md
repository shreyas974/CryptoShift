# CryptoShift web app: security model

This document covers the web application in `cryptoshift_app/` (Node.js API + React UI). It states what
the app protects, how, and what it does **not** protect. It has not been independently audited.

## What the app does

CryptoShift scans a repository for quantum-vulnerable cryptography (RSA, ECDSA/ECDH, SHA-1), proposes
replacement patches (ML-KEM / ML-DSA), **runs real tests** on each candidate in throwaway copies, and only
lets a human reviewer approve a candidate whose required checks all passed. Released patches are written to a
working copy with a byte-for-byte rollback checkpoint.

The app itself does not encrypt user data and does not implement any cryptographic algorithm. It relies on
Node.js's built-in `crypto` module (OpenSSL) for hashing, HMAC, scrypt and random numbers.

## Assets

| Asset | Why it matters |
|---|---|
| Approval decisions and releases | They change code that protects banking traffic. Forged approvals defeat the whole gate. |
| Audit log | Evidence of who did what. Must be trustworthy after the fact. |
| Account passwords and sessions | Control who can approve and release. |
| Repository working copies | Released patches modify these files. |
| `SARVAM_API_KEY` (optional) | Third-party API credential. |

## Threats and controls

| Threat | Control | Where |
|---|---|---|
| Someone approves under another person's name | Approvals use the signed-in account. Any `reviewer`/`actor` field in a request is ignored. | `patches.js` `decide()` |
| One person verifies and approves their own patch | Four-eyes rule: whoever started the verification run cannot approve it. | `patches.js` |
| Anonymous access | Every API route except `/api/health` and sign-in requires a session. | `server.js` routing |
| Privilege misuse | Roles `viewer < engineer < reviewer < admin`; each route declares its minimum role. | `server.js`, `auth.js` |
| Cross-site request forgery | Session cookie is `HttpOnly; SameSite=Strict`. Every POST must send the per-session CSRF token in `X-CSRF-Token` and a JSON content type (text/plain "simple requests" get 415). No CORS headers are sent. | `server.js` `dispatch()` |
| Password guessing | 5 failed sign-ins per IP+username lock sign-in for 15 minutes. Same error and similar timing for unknown users and wrong passwords. | `auth.js` `login()` |
| Password database theft | scrypt (N=2^15, r=8, p=3, 32-byte random salt, OWASP-recommended parameters), constant-time comparison. Minimum 15 characters (NIST SP 800-63B). `users.json` is mode 0600. | `auth.js` |
| Session theft | 256-bit random tokens; the server stores only their SHA-256. 8 h absolute and 1 h idle expiry. Password change signs out other sessions; disabling an account or changing its role ends its sessions. | `auth.js` |
| First-admin takeover on a fresh install | The first account needs a one-time setup code printed on the server console (or `CRYPTOSHIFT_SETUP_TOKEN` on hosted deployments). | `auth.js` `setup()` |
| Audit log tampering | Append-only JSONL. Each entry carries `HMAC-SHA256(key, entry ‖ previous MAC)`, so an edit, deletion, reordering or forged entry is detected by `/api/audit/verify` (shown on Reports & Audit). State resets do not erase the log. | `auditlog.js` |
| Path traversal | Repository ids must match an existing workspace; file paths are resolved with `realpath` and rejected if they leave the repository (`..`, absolute paths, symlinks). | `repos.js` `resolveInRepo()` |
| Malformed input / denial of service | Malformed URLs give 400 instead of crashing the process. Bodies over 64 KB give 413. Request and header timeouts are set. At most 2 verification runs at once (429 otherwise). Verification processes are killed after 60 s. | `server.js`, `verify.js` |
| Secrets reaching code under test | Verification subprocesses get a minimal environment (PATH, HOME, locale), not the server's environment. | `verify.js` `run()` |
| Error-message leakage | Unexpected errors return `Internal server error`; details go to the server log only. `/api/health` reveals only status and version. | `server.js` |
| XSS / clickjacking | React escapes output. CSP `default-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'`, plus `nosniff`, `Referrer-Policy: no-referrer`, COOP/CORP and a restrictive `Permissions-Policy`. HSTS when served over HTTPS. | `server.js` `SECURITY_HEADERS` |
| Prompt injection via repository content (AI review) | Repository text is fenced and marked as data. AI output is labelled advisory and can never unlock approval. | `server.js` `sarvam-analyze` routes |
| Supply chain | The backend has zero npm dependencies. The frontend has 3 runtime dependencies (React, React DOM, React Router); CI fails on high/critical `npm audit` findings. | `package.json`, CI |

## Known limitations (read before deploying)

- **Audit-log truncation.** A hash chain detects edits but not the silent removal of the newest entries.
  Copy the chain head shown on *Reports & Audit* into an external system (ticket, email) from time to time;
  if the log is ever cut short, the old head will no longer appear.
- **The HMAC key is on the same host as the log** (`audit.key`, mode 0600). An attacker with that key, or
  with root on the server, can rewrite the log. For stronger guarantees, ship entries to an external
  write-once store.
- **Sessions live in memory.** A restart signs everyone out, and several server instances do not share sessions.
- **Vercel / serverless** keeps data in `/tmp`, which is temporary. Accounts, state and the audit log
  disappear when an instance is recycled. Use it for demos only; deploy the Docker image with a persistent
  volume for real use.
- **No multi-factor authentication or SSO yet.** Put the app behind your identity provider's reverse proxy
  for MFA in production.
- **Verification runs repository code.** Only bundled sample repositories are registered, and nothing can be
  uploaded through the UI. If you register your own repositories, run the server in the provided container
  (non-root, read-only root filesystem), because the repository's tests execute on that host.
- **Parameter conformance is a size check against FIPS 203/204 tables, not a known-answer test** of an ML-KEM or
  ML-DSA implementation. The sample repository has no real PQC implementation to test.
- **The HTTP server does not terminate TLS.** Put it behind a TLS-terminating proxy and set
  `CRYPTOSHIFT_SECURE_COOKIE=1` so cookies get the `Secure` flag and HSTS is sent.

## Verification

`npm test` runs:

- `tests/unit.test.mjs`: the RFC 7914 scrypt and RFC 4231 HMAC-SHA256 known-answer vectors, password hashing, the
  password policy, the role order, audit-chain tamper detection (edit, delete, reorder, forged MAC, and an
  attacker without the key), the session lifecycle, and the NIST deadlines.
- `tests/api.test.mjs`: 37 end-to-end checks against a real server in a temporary data directory. They cover:
  - authentication and access control (401/403)
  - CSRF, including cross-site simple requests
  - sign-in throttling and enumeration resistance
  - security headers
  - malformed-URL survival, path traversal and oversized bodies
  - error leakage, the four-eyes rule and identity binding
  - the full verify → approve → release → rollback flow
  - audit-chain verification and tamper detection after a restart
  - CycloneDX 1.6 CBOM export

The CBOM output was also validated against the official CycloneDX 1.6 JSON schema (0 errors), and a deliberately
broken CBOM was confirmed to be rejected.

## Reporting a vulnerability

Please open a private security advisory on the GitHub repository instead of a public issue.
