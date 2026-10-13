"""
app/modules/documents/repositories/document_repository.py

Repositori data dokumen karyawan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.5.
"""
from app.crud.crud_document import CRUDDocument


class DocumentRepository(CRUDDocument):
    """
    Repositori akses data dokumen pribadi karyawan, antrean verifikasi, dan masa kedaluwarsa.
    """
