"""
app/core/signing.py
Penandatangan dokumen (fase 6, dok 02 A-09, dok 08). Yang ditandatangani adalah payload JSON kanonik
(RFC 8785), bukan PDF. Antarmuka `DocumentSigner` dibuat agar implementasi lokal (kunci dari lingkungan,
untuk dev/staging) bisa diganti adaptor KMS/HSM sebelum produksi tanpa mengubah pemanggil.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Any, Protocol

import rfc8785
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.config import settings


def canonical(payload: dict[str, Any]) -> bytes:
    """Bentuk kanonik RFC 8785 — dipakai bersama oleh penandatanganan dan verifikasi."""
    return rfc8785.dumps(payload)


class DocumentSigner(Protocol):
    algorithm: str
    kms_ref: str

    @property
    def public_key(self) -> bytes: ...

    @property
    def fingerprint(self) -> str: ...

    def sign(self, message: bytes) -> bytes: ...


class LocalEd25519Signer:
    """Kunci Ed25519 dari `DOC_SIGNING_KEY_HEX` (32 byte seed). BUKAN untuk produksi (dok 08: kunci di KMS)."""
    algorithm = "Ed25519"

    def __init__(self, seed_hex: str, kms_ref: str) -> None:
        self._key = (Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex)) if seed_hex
                     else Ed25519PrivateKey.generate())
        self.kms_ref = kms_ref if seed_hex else "ephemeral:dev"

    @property
    def public_key(self) -> bytes:
        return self._key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.public_key).hexdigest()[:16]

    def sign(self, message: bytes) -> bytes:
        return self._key.sign(message)


@lru_cache(maxsize=1)
def get_document_signer() -> DocumentSigner:
    return LocalEd25519Signer(settings.DOC_SIGNING_KEY_HEX, settings.DOC_SIGNING_KMS_REF)
