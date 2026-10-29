# Member 3 migration plan (generated)

Generated 2026-10-29T11:17:58+00:00 from `demo_bank_app/configs` (SYNTHETIC demo bank). Plan hash `ac4ea7e56f24a867`.

## Services

| Service | Evidence | Findings | Risk (provisional) | Wave | Gate state | Blocking |
|---|---|---|---|---|---|---|
| auth_gateway | OBSERVED | 4 | 13.3 | 1 | PROPOSED | purpose_resolved |
| card_vault | OBSERVED | 2 | 5.9 | 2 | READY | - |
| interbank_tls | OBSERVED | 5 | 13.5 | 0 | READY | - |
| ledger_audit | DECLARED_ONLY | 0 | 7.75 | 0 | PROPOSED | purpose_resolved |
| payment_signing | OBSERVED | 2 | 7.8 | 1 | READY | - |
| settlement_batch | DECLARED_ONLY | 0 | 7.85 | 2 | PROPOSED | purpose_resolved |

## Schedule

Objective 299.1; waves {'0': ['interbank_tls', 'ledger_audit'], '1': ['auth_gateway', 'payment_signing'], '2': ['card_vault', 'settlement_batch']}; dependency violations 0.
Sensitivity: rank changed in 6/10 weight perturbations, schedule changed in 3/10.

## Dependency graph

Edges by provenance {'OBSERVED': 4, 'DECLARED': 5, 'INFERRED': 0}; cycles none; conflicts 3.

- interbank_tls -> settlement_batch: DECLARED in descriptor but no OBSERVED evidence in scanned files
- ledger_audit -> interbank_tls: OBSERVED in code/config but not DECLARED in descriptor
- payment_signing -> settlement_batch: DECLARED in descriptor but no OBSERVED evidence in scanned files

## Rollback

restore the profile copy from snapshot sha256:457d33bd76ef598f3d9715d8bde0dddee2c6ee56f233ebdefc35953e78003421; rehearsal {'forced_failure_detected': True, 'restored_hash_matches_snapshot': True, 'recovered': True, 'originals_unchanged': True}.
- WARNING: Restored profile still enables 3DES (DES-CBC3-SHA); NIST SP 800-131A disallows it - compensating control or cipher clean-up needed
- WARNING: Never restore SHA-1 or 3DES configurations as a rollback target; fall back to SHA-256 / AES-256-GCM classical baselines.

## Approval

Approved steps: none (human-only CLI).

Scope: Generic loopback lab evidence (OpenSSL 3.5 s_server/s_client, test keys). It does NOT exercise the service's own stack (e.g. KMS key wrapping, JWT libraries, partner peers); READY means 'eligible for human review', not 'verified in production'.
