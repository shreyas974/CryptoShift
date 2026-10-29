"""Append-only ledger with encrypted records."""

from shared.bankcrypto import primitives

RECORD_CIPHER = "AES-256-GCM"
_records = []


def record(body: bytes):
    sealed = primitives.seal("AES-256-GCM", "ledger-2026", body)
    _records.append({"sealed": sealed, "check": primitives.checksum("SHA1", body)})
    return len(_records)


def integrity_digest(body: bytes):
    return primitives.checksum("SHA1", body)
