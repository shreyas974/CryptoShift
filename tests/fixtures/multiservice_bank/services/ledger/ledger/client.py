"""SYNTHETIC fixture: ledger client."""

import hashlib


def post_entry(payload: bytes) -> str:
    return hashlib.sha1(payload).hexdigest()
