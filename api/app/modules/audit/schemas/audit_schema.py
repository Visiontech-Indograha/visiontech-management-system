"""
app/schemas/audit.py

Request and response schemas for system audit logs.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    """
    Schema for an individual audit event.
    """
    id: UUID
    occurred_at: datetime
    # Label pelaku tindakan audit
    actor_label: str
    action: str
    entity_type: str
    entity_id: UUID | None = None
    detail: str | None = None
    # Perubahan data secara spesifik jika ada
    changes: dict[str, Any] | None = None


class AuditEventListResponse(BaseModel):
    """
    Schema for paginated list of audit events.
    """
    items: list[AuditEventResponse]
    total: int
    page: int
    size: int
