"""Web banking portal backend-for-frontend."""

from services.api_gateway import gateway


def start_payment(token, payer, payee, amount_minor):
    return gateway.pay(token, payer, payee, amount_minor)
