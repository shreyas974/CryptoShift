"""Derives per-session keys between the mobile app and auth."""

from shared.bankcrypto import primitives
from services.payments import limits

SESSION_KEY_AGREEMENT = primitives.generate_keypair("ECDH-P256")


def session_for(customer_id: str):
    return {
        "customer": customer_id,
        "kex": SESSION_KEY_AGREEMENT.algorithm,
        "daily_limit": limits.daily_limit_for(customer_id),
    }
