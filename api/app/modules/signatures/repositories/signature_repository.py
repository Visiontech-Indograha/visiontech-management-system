"""
app/modules/signatures/repositories/signature_repository.py

Repositori data tanda tangan dokumen SK.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.5.
"""
from app.crud.crud_signature import CRUDSignature


class SignatureRepository(CRUDSignature):
    """
    Repositori akses data tanda tangan digital, kunci publik, dan histori dokumen SK.
    """
