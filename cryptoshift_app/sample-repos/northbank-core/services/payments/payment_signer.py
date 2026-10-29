"""Signs payment instructions sent to the settlement network."""

from shared.bankcrypto import primitives
from services.auth import token_service
from services.ledger import ledger_store

INSTRUCTION_KEY = primitives.generate_keypair("ECDSA-P256")


def sign_instruction(payer: str, payee: str, amount_minor: int):
    body = f"{payer}>{payee}:{amount_minor}".encode()
    ledger_store.record(body)
    return {"body": body, "sig": primitives.sign(INSTRUCTION_KEY, body)}


def authorised(token):
    return token_service.verify_token(token)
