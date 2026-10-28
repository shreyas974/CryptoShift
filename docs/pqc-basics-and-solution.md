# Post-Quantum Cryptography Basics and CryptoShift Solution Overview

This document summarizes the cryptographic standards and migration architecture behind **CryptoShift (Quant-A-Maze 3.0 — PQC-01)** and links to the full project deliverables in [`assets/`](../assets/).

---

## 1. Reference Deliverables in `assets/`

- **Concept & Solution Guide (Word Document):** [CryptoShift_PQC_Concept_and_Solution_Guide.docx](../assets/CryptoShift_PQC_Concept_and_Solution_Guide.docx)
- **Mentor Presentation Deck (PowerPoint):** [CryptoShift_Mentor_Deck.pptx](../assets/CryptoShift_Mentor_Deck.pptx)

> **Scope Reminder:** The concept guide and mentor deck explain the broader problem motivation and target architecture. Refer to [`src/cryptoshift/`](../src/cryptoshift/), [`reports/qpiai/qpiai_evidence_report.md`](../reports/qpiai/qpiai_evidence_report.md), and [`reports/evaluation/evaluation_report.md`](../reports/evaluation/evaluation_report.md) for the exact verified prototype implementation.

---

## 2. NIST Post-Quantum Cryptography Standards & Operation Roles

A common mistake in automated migration tools is replacing an algorithm name (`RSA` or `ECC`) without checking **what cryptographic operation** it performs. CryptoShift enforces strict role separation:

| Operation Purpose | Vulnerable Legacy Primitives | Primary Quantum Threat | NIST PQC Standard | Target Transitional / Hybrid Role |
|---|---|---|---|---|
| **Key Establishment / Encapsulation** | `ECDHE-P256`, `DH-2048`, `RSA-2048` (OAEP key transport/wrapping) | Shor's algorithm + **Harvest-Now-Decrypt-Later (HNDL)** | **FIPS 203 (`ML-KEM`)** | `X25519MLKEM768` (TLS/mTLS) or `ML-KEM-768` hybrid DEK encapsulation |
| **Digital Signatures & Authentication** | `RSA-2048` (RS256, XMLDSig), `ECDSA-P256` (ES256) | Shor's algorithm (forgery once CRQC exists) | **FIPS 204 (`ML-DSA`)** / **FIPS 205 (`SLH-DSA`)** | `ML-DSA-65` dual-signature with `RSA-2048` or `ECDSA-P256` |
| **Symmetric Encryption** | `3DES` (Triple-DES) | Grover's algorithm + Sweet32 64-bit block collision | **NIST SP 800-38D** | `AES-256-GCM` |
| **Message Digests / Hashing** | `SHA-1` | Classical collision attacks + Grover preimage reduction | **FIPS 202 (`SHA-3`)** | `SHA3-256` or `SHA-384` |

If the scanner detects an algorithm clue (e.g., `LEGACY_RSA_2048_CONFIG`) where the `operation_purpose` is `"unknown"`, CryptoShift places the recommendation on **`HOLD`** for human security review rather than guessing between `ML-KEM` and `ML-DSA`.

---

## 3. Why Verification-Gated Waves Matter in Banking

1. **Upstream Key & Trust Dependencies:** A downstream service (such as `payment_signing` or `settlement_batch`) cannot promote hybrid PQC signatures until its upstream identity provider (`auth_gateway`), audit notarizer (`ledger_audit`), and mTLS transport (`interbank_tls`) support the new certificate and token formats.
2. **Wire-Size & Middlebox Constraints:** Hybrid `X25519MLKEM768` + `ML-DSA-65` handshakes add ~7.1 KB to envelope headers, exceeding a single 1500-byte Ethernet MTU. Every wave requires compatibility and latency gate checks before promotion.
3. **Safe Rollback Policy:** Every migration wave records a pre-wave snapshot and feature flag (`CRYPTOSHIFT_ENABLE_HYBRID_PQC=false`), while warning operators if reverting to deprecated legacy algorithms (`SHA-1`, `3DES`) would violate baseline security policy.

