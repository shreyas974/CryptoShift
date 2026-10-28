# Synthetic Banking Application (`demo_bank_app`)

This directory contains a **synthetic banking microservice suite** created for **Quant-A-Maze 3.0 — PQC-01: Verification-Gated Cryptographic Migration Across Banking Applications**.

> **Note:** All cryptographic keys, certificates, endpoints, and transaction payloads in this folder are 100% synthetic and contain no real credentials or customer data.

## Service Architecture & Dependency DAG

| Service ID | Banking Role | Legacy Primitives | Target PQC / Hybrid Replacement | Upstream Dependencies | Duration (min) | Verification Ready (Wave 0) |
|---|---|---|---|---|---:|---|
| `auth_gateway` | Customer & API JWT/OAuth token signing | `RSA-2048`, `SHA-1` | `ML-DSA-65 (FIPS 204) + RSA-2048 Hybrid`, `SHA3-256` | *(root)* | 35 | Yes |
| `ledger_audit` | Immutable core-banking ledger notarization | `ECDSA-P256`, `SHA-1` | `ML-DSA-65 (FIPS 204)`, `SHA3-256` | *(root)* | 30 | Yes |
| `interbank_tls` | Interbank SWIFT/ISO-20022 mTLS gateway | `ECDHE-RSA-P256`, `RSA-2048` | `X25519MLKEM768 (FIPS 203 Hybrid)`, `ML-DSA-65` | *(root)* | 40 | Yes |
| `card_vault` | PCI card token vault & envelope encryption | `RSA-2048`, `3DES` | `ML-KEM-768 (FIPS 203)`, `AES-256-GCM` | `auth_gateway` | 35 | No (requires vault KAT gate) |
| `payment_signing` | Real-time RTGS/UPI payment instruction signing | `ECDSA-P256`, `RSA-2048` | `ML-DSA-65 (FIPS 204) Dual-Sign` | `auth_gateway`, `ledger_audit` | 45 | Yes |
| `settlement_batch` | End-of-day clearinghouse settlement archive | `DH-2048`, `RSA-2048`, `3DES` | `ML-KEM-768 (FIPS 203)`, `SLH-DSA-128s (FIPS 205)`, `AES-256-GCM` | `payment_signing`, `interbank_tls` | 50 | No (requires downstream partner window) |
