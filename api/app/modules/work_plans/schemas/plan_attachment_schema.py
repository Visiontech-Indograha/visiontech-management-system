"""Skema permintaan & respons: plan attachment (dipindah dari api/v1/endpoints/work_plan_attachments.py, R-28 M2b)."""
from uuid import UUID

from pydantic import BaseModel


class AttachmentsRequest(BaseModel):
    """Permintaan untuk menautkan satu atau lebih file sebagai lampiran.

    Skema ini memuat daftar ID file yang ingin dilampirkan pada suatu rencana kerja.
    """
    file_ids: list[UUID]  # Daftar ID file (UUID) yang menjadi lampiran


class AttachmentResponse(BaseModel):
    """Respons yang menyajikan detail metadata dari file lampiran.

    Berisi informasi dasar seperti nama file, tipe MIME, ukuran, serta urutan tampilannya.
    """
    file_id: str  # ID file lampiran
    file_name: str  # Nama asli file lampiran
    mime_type: str  # Tipe MIME dari file (misal: image/jpeg, application/pdf)
    byte_size: int  # Ukuran file dalam ukuran byte
    sort_order: int  # Urutan tampilan lampiran

