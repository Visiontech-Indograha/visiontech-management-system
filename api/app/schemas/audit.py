from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class AuditEventResponse(BaseModel):
    id: UUID
    occurred_at: datetime
    actor_label: str
    action: str
    entity_type: str
    entity_id: Optional[UUID] = None
    detail: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None

class AuditEventListResponse(BaseModel):
    items: List[AuditEventResponse]
    total: int
    page: int
    size: int
