"""Customer payment limits, read by payments and (for display) by auth."""

from services.auth import token_service

DEFAULT_DAILY_LIMIT = 250_000


def daily_limit_for(customer_id: str):
    return DEFAULT_DAILY_LIMIT


def limit_token(customer_id: str):
    return token_service.issue_token(customer_id)
