"""Vendored third-party HSM client (legacyhsm 2.4.1). Do not edit in place."""

from shared.bankcrypto import primitives

VERSION = "2.4.1"


class HsmClient:
    def __init__(self):
        # Transport key used to wrap exported keys for the HSM.
        self.transport_key = primitives.generate_keypair("RSA", 1024)

    def wrap_key(self, label: str):
        return primitives.sign(self.transport_key, label.encode())
