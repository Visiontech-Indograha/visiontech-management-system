"""
app/crud/crud_signature.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.signatures.repositories.signature_repository import (
    CRUDSignature,
    SignatureRepository,
)

__all__ = ["CRUDSignature", "SignatureRepository"]
