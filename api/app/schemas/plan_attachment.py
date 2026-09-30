"""Skema permintaan & respons: plan attachment (dipindah dari api/v1/endpoints/work_plan_attachments.py, R-28 M2b)."""
from uuid import UUID

from pydantic import BaseModel


class AttachmentsRequest(BaseModel):
    file_ids: list[UUID]


class AttachmentResponse(BaseModel):
    file_id: str
    file_name: str
    mime_type: str
    byte_size: int
    sort_order: int
