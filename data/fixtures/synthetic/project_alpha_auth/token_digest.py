"""Synthetic fixture SYN-002: SHA-1 message digest."""

import hashlib


def legacy_thumbprint(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()

