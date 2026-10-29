"""Issues signed access tokens for customer sessions."""

from shared.bankcrypto import primitives
from shared.pki import cert_authority

TOKEN_TTL_SECONDS = 900
SIGNING_KEY = primitives.generate_keypair("RSA", 2048)


def issue_token(customer_id: str):
    claims = f"sub={customer_id};ttl={TOKEN_TTL_SECONDS}".encode()
    return {"claims": claims, "sig": primitives.sign(SIGNING_KEY, claims)}


def verify_token(token):
    return primitives.verify(SIGNING_KEY, token["claims"], token["sig"])


def service_certificate():
    return cert_authority.issue_certificate("auth")
