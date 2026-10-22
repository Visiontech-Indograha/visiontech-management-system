"""
app/modules/notifications/dependencies.py

Perakitan service modul notifications untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.notifications.services.notification_service import NotificationService


def get_notification_service(db: AsyncSession = Depends(get_db_with_user)) -> NotificationService:
    return NotificationService(db)
