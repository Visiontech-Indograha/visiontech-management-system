"""
app/modules/signatures/services/signature_service.py

Layanan logika bisnis untuk modul tanda tangan elektronik dan verifikasi QR.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.3.
"""

from app.services.signature_service import (
    ACCEPTOR,
    APPROVER,
    ISSUER,
    qr_png_data_uri,
    verify_url,
)
from app.services.signature_service import (
    SignatureService as BaseSignatureService,
)


class SignatureService(BaseSignatureService):
    """
    Layanan bisnis tanda tangan elektronik.
    Mengelola penandatanganan dokumen kanonik, pembuatan QR verifikasi, dan pencabutan tanda tangan.
    """


__all__ = [
    "ACCEPTOR",
    "APPROVER",
    "ISSUER",
    "SignatureService",
    "qr_png_data_uri",
    "verify_url",
]
