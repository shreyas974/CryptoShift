"""Synthetic Banking Fixture: Real-Time Payment Instruction Signer (`payment_signing`)."""

SERVICE_ID = "payment_signing"
OWNER = "Real-Time Payments Team"
DEPENDS_ON = ["auth_gateway", "ledger_audit"]

# Digital signature primitives -> must migrate to ML-DSA-65 (FIPS 204), NEVER ML-KEM
PRIMARY_SIGNATURE_SCHEME = "ECDSA_P256"
FALLBACK_XMLDSIG_SCHEME = "RS256"
