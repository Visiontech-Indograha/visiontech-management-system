"""app/shared/attachments/schema.py - bentuk data lampiran pengajuan."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AttachmentAdd(BaseModel):
    file_id: UUID = Field(description="ID berkas hasil POST /files/upload (unggahan sendiri)")


class AttachmentOut(BaseModel):
    file_id: UUID
    file_name: str
    mime_type: str
    byte_size: int
    mine: bool = Field(description="true bila diunggah oleh pemanggil (boleh dihapus selama pengajuan menunggu)")
    created_at: datetime
