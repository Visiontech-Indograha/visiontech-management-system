"""
app/core/signing.py

Document signer configuration and utilities.
This module handles the signing of canonical JSON payloads (RFC 8785)
rather than PDF files. The `DocumentSigner` interface is provided so that
the local implementation can be replaced with a KMS/HSM adapter before production.
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
    """
    Generate canonical form of the given payload using RFC 8785.
    Shared across both signing and verification processes.
    """
    # Menghasilkan byte kanonik RFC 8785
    return rfc8785.dumps(payload)


class DocumentSigner(Protocol):
    """
    Protocol defining the required properties and methods for document signers.
    """
    algorithm: str
    kms_ref: str

    @property
    def public_key(self) -> bytes:
        """Retrieve the public key bytes."""
        ...

    @property
    def fingerprint(self) -> str:
        """Retrieve the short fingerprint of the public key."""
        ...

    def sign(self, message: bytes) -> bytes:
        """Sign a message and return the resulting signature bytes."""
        ...


class LocalEd25519Signer:
    """
    Local implementation of the document signer using Ed25519 keys.
    Key is derived from `DOC_SIGNING_KEY_HEX` (32 bytes seed).
    WARNING: Not for production use.
    """
    algorithm = "Ed25519"

    def __init__(self, seed_hex: str, kms_ref: str) -> None:
        # Menggunakan kunci dari seed hex atau membuat kunci baru
        self._key = (Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex)) if seed_hex
                     else Ed25519PrivateKey.generate())
        # Menetapkan referensi KMS
        self.kms_ref = kms_ref if seed_hex else "ephemeral:dev"

    @property
    def public_key(self) -> bytes:
        """Retrieve the raw public key bytes associated with the signer."""
        # Mengembalikan public key dalam bentuk mentah
        return self._key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)

    @property
    def fingerprint(self) -> str:
        """Generate a short 16-character SHA-256 fingerprint of the public key."""
        # Membuat sidik jari berdasarkan public key
        return hashlib.sha256(self.public_key).hexdigest()[:16]

    def sign(self, message: bytes) -> bytes:
        """Sign the provided message using the private key."""
        # Menandatangani pesan dengan private key
        return self._key.sign(message)


@lru_cache(maxsize=1)
def get_document_signer() -> DocumentSigner:
    """
    Factory function to retrieve a cached DocumentSigner instance.
    """
    # Mengambil signer dengan cache untuk penggunaan aplikasi
    return LocalEd25519Signer(settings.DOC_SIGNING_KEY_HEX, settings.DOC_SIGNING_KMS_REF)
