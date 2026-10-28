"""Synthetic fixture SYN-008: Dynamic reflection call (illustrates static analysis FN)."""

import hashlib


def obfuscated_digest(payload: bytes) -> str:
    fn = getattr(hashlib, "sh" + "a1")
    return fn(payload).hexdigest()

