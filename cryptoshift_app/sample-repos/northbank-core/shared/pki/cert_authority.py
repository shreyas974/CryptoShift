"""Internal certificate authority for service-to-service TLS."""

from shared.bankcrypto import primitives
from vendor.legacy_hsm_client.client import HsmClient

CA_KEY = primitives.generate_keypair("RSA", 3072)
VALIDITY_DAYS = 825


def issue_certificate(service_name: str):
    hsm = HsmClient()
    wrapped = hsm.wrap_key(service_name)
    body = f"CN={service_name};days={VALIDITY_DAYS}".encode()
    return {
        "subject": service_name,
        "signature": primitives.sign(CA_KEY, body),
        "wrapped_key": wrapped,
    }
