"""
app/modules/notifications/controllers/notification_controller.py

Controller orkestrasi use case notifikasi pengguna.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.notifications.dependencies import get_notification_service
from app.modules.notifications.schemas.notification_schema import NotificationList, NotificationOut
from app.modules.notifications.services.notification_service import NotificationService


class NotificationController:
    """
    Controller use case notifikasi pengguna.
    """

    def __init__(
        self,
        notification_service: NotificationService = Depends(get_notification_service),
    ) -> None:
        self.service = notification_service

    async def handle_list_notifications(
        self,
        current_user: CurrentUser,
        unread_only: bool = False,
        limit: int = 50,
    ) -> NotificationList:
        """Mengambil daftar notifikasi milik pengguna saat ini."""
        rows = await self.service.list_for(current_user.user_id, unread_only, limit)
        return NotificationList(
            unread=await self.service.unread_count(current_user.user_id),
            items=[NotificationOut(**r._mapping) for r in rows],
        )

    async def handle_read_all(self, current_user: CurrentUser) -> dict[str, int]:
        """Menandai semua notifikasi milik pengguna saat ini sebagai telah dibaca."""
        return {"updated": await self.service.mark_read(current_user.user_id, None)}

    async def handle_read_one(self, current_user: CurrentUser, notification_id: UUID) -> dict[str, int]:
        """Menandai satu notifikasi tertentu sebagai telah dibaca."""
        return {"updated": await self.service.mark_read(current_user.user_id, notification_id)}


__all__ = ["NotificationController"]
