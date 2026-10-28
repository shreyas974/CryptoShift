# Migration verification and rollback

## Mapping rules

Classify the operation before recommending a candidate. ML-KEM is a key-establishment mechanism. ML-DSA and SLH-DSA are signature schemes. RSA or elliptic-curve references may serve different purposes; do not perform blanket name-based replacement.

## Verification gate

For each proposed wave, retain the input revision, finding IDs, dependency prerequisites, old/new peer combinations, expected behavior, observed result, trace reference, size/timing method, approver, and status. A changed configuration alone does not mean migration is verified.

Use real library/protocol traces only when produced by the actual supported implementation. Label modelled or mocked traces directly in the report. Never include credentials, private keys, session secrets, or customer data in traces.

## Rollback record

Record the known-good configuration/version, feature-flag or restoration steps, owner, measurable stop trigger, downstream compatibility, and re-verification steps. State if reverting to the old algorithm would violate policy or is not allowed.