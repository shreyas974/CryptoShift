"""Mobile app backend: session setup and push notifications."""

from services.api_gateway import gateway
from services.auth import session_keys


def open_session(customer_id: str):
    return {"session": session_keys.session_for(customer_id), "tls": gateway.tls_policy()}
