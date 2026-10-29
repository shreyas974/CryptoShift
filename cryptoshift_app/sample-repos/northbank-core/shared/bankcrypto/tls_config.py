"""Shared TLS policy used by every NorthBank service."""

MIN_VERSION = "TLSv1.2"

# Key-exchange groups offered by NorthBank servers, in preference order.
KEY_EXCHANGE_GROUPS = ["X25519", "ECDH-P256"]

# Server certificate signature algorithm issued by the internal CA.
CERT_SIGNATURE = "RSA-3072"

CIPHER_SUITES = ["TLS_AES_256_GCM_SHA384", "TLS_AES_128_GCM_SHA256"]


def server_policy():
    return {
        "min_version": MIN_VERSION,
        "groups": list(KEY_EXCHANGE_GROUPS),
        "cert_signature": CERT_SIGNATURE,
        "suites": list(CIPHER_SUITES),
    }
