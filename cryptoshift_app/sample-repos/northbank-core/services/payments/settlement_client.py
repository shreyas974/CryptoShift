"""Client for the external settlement network."""

from shared.bankcrypto import tls_config

# Signature algorithms the settlement network currently accepts on instructions.
SETTLEMENT_ACCEPTED = ("ECDSA-P256", "RSA-2048")


def connection_policy():
    return tls_config.server_policy()


def accepts(signature_algorithm: str):
    return signature_algorithm in SETTLEMENT_ACCEPTED
