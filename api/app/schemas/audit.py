from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: UUID
    occurred_at: datetime
    actor_label: str
    action: str
    entity_type: str
    entity_id: UUID | None = None
    detail: str | None = None
    changes: dict[str, Any] | None = None

class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
    page: int
    size: int
