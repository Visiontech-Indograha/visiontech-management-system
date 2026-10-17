"""
app/modules/notifications/routes/notification_route.py

Rute endpoint HTTP untuk notifikasi pengguna (/notifications).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.notifications.controllers.notification_controller import NotificationController
from app.modules.notifications.schemas.notification_schema import NotificationList

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationList)
async def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user),
    controller: NotificationController = Depends(),
) -> NotificationList:
    """
    Mengambil daftar notifikasi milik pengguna saat ini.

    Query params:
    - unread_only: Filter hanya notifikasi yang belum dibaca (default False)
    - limit: Maksimum jumlah notifikasi yang dikembalikan (default 50)

    Return: Daftar notifikasi beserta jumlah notifikasi belum dibaca (NotificationList)
    """
    return await controller.handle_list_notifications(current_user, unread_only=unread_only, limit=limit)


@router.post("/read-all")
async def read_all(
    current_user: CurrentUser = Depends(get_current_user),
    controller: NotificationController = Depends(),
) -> dict[str, int]:
    """
    Menandai semua notifikasi milik pengguna saat ini sebagai telah dibaca.

    Return: Jumlah notifikasi yang berhasil diperbarui
    """
    return await controller.handle_read_all(current_user)


@router.post("/{notification_id}/read")
async def read_one(
    notification_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: NotificationController = Depends(),
) -> dict[str, int]:
    """
    Menandai satu notifikasi tertentu sebagai telah dibaca.

    Path params:
    - notification_id: UUID dari notifikasi

    Return: Jumlah notifikasi yang berhasil diperbarui (idealnya 1)
    """
    return await controller.handle_read_one(current_user, notification_id)


__all__ = ["router"]
