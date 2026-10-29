"""Public API gateway in front of auth and payments."""

from shared.bankcrypto import tls_config
from services.auth import token_service
from services.payments import payment_signer


def tls_policy():
    return tls_config.server_policy()


def pay(token, payer, payee, amount_minor):
    if not token_service.verify_token(token):
        return {"status": 401}
    return {"status": 202, "instruction": payment_signer.sign_instruction(payer, payee, amount_minor)}
