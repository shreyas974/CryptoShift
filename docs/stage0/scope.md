# Stage 0 — Scope

## Problem (official, Quant-A-Maze 3.0 PQC-01)

A bank has RSA/ECC-dependent services, certificates and software dependencies that cannot all move to post-quantum
cryptography at once without interrupting payments. Identify current cryptographic exposure and prioritise a
provably compatible migration schedule.

**Deliver:** inventory with file/service evidence; migration sequence; working before-and-after protocol traces;
compatibility tests; rollback plan.
**Evaluate:** detection precision/recall on labelled code and configs; protocol correctness; overhead; feasible
migration dependencies.

No other rubric items or weights are assumed.

## What CryptoShift is

A hackathon **prototype** that helps a human plan a verification-gated migration. It is **not** a production
migration service, a scanner certified for bank estates, or a certification tool. Every proposed PQC target is a
**candidate for human review**; nothing is changed automatically outside an isolated staging copy.

## In scope for Stage 0 + Stage 1 (this branch)

| Area | Stage 1 deliverable |
|---|---|
| Inventory | Additive detectors in `src/cryptoshift/inventory/` (Python AST, nginx/Apache/openssl.cnf, dependency manifests, certificate metadata) producing a CBOM-like JSON + Markdown |
| Data | Read-only dataset registry, `data-summary` command, dataset documentation |
| Evaluation | Labelling guidelines, real public-code labels split by repository, precision/recall on that set only |
| Governance | Claims register, requirements traceability, data/secrets policy, evidence log |

## Out of scope now (PLANNED, not started)

- Deriving migration tasks from real scanner findings (tasks still come from `demo_bank_app/services.py`).
- Real verification gates, real before/after protocol traces, compatibility matrices.
- Rollback automation beyond the existing prototype records.
- UI work (Member 4), QpiAI work, ML training.

## Constraints

- Only systems the team owns are scanned; no live-bank or third-party scanning.
- Datasets are read-only; large files never enter Git; secrets never leave `.env` / `qcloud.env`.
- Crypto roles are fixed: ML-KEM (FIPS 203) = key establishment only; ML-DSA (FIPS 204) / SLH-DSA (FIPS 205) =
  signatures only. Unknown purpose ⇒ HOLD for human review.
- The risk score (`src/cryptoshift/scoring.py`) is **provisional and unvalidated** (see
  [requirements-traceability.md](requirements-traceability.md)).

See also: [architecture-overview.md](architecture-overview.md), [claims-register.md](claims-register.md).
