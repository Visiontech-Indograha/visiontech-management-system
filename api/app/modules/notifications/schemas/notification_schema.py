"""
app/modules/notifications/schemas/notification_schema.py

Skema respons notifikasi pengguna.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.4.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: UUID
    kind: str
    title: str
    body: str
    daily_plan_id: UUID | None = None
    target: str | None = None
    created_at: datetime
    read_at: datetime | None = None


class NotificationList(BaseModel):
    unread: int
    items: list[NotificationOut]
