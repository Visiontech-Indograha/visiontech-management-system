"""
app/modules/documents/services/document_service.py

Layanan logika bisnis untuk modul dokumen karyawan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.3.
"""
from app.services.document_service import DocumentService as BaseDocumentService


class DocumentService(BaseDocumentService):
    """
    Layanan bisnis dokumen karyawan.
    Mengelola aturan verifikasi, batas akses dokumen pribadi, dan status kedaluwarsa.
    """


__all__ = ["DocumentService"]
