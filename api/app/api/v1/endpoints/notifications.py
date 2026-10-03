"""
Notifikasi dalam aplikasi (alur SK v2): lonceng di web, daftar di HP. Hanya milik pengguna sendiri.
"""
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_notification_service
from app.core.security import CurrentUser
from app.schemas.plan_draft import NotificationList, NotificationOut
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationList)
async def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationList:
    rows = await notification_service.list_for(current_user.user_id, unread_only, limit)
    return NotificationList(unread=await notification_service.unread_count(current_user.user_id),
                            items=[NotificationOut(**r._mapping) for r in rows])


@router.post("/read-all")
async def read_all(
    current_user: CurrentUser = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> dict[str, int]:
    return {"updated": await notification_service.mark_read(current_user.user_id, None)}


@router.post("/{notification_id}/read")
async def read_one(
    notification_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> dict[str, int]:
    return {"updated": await notification_service.mark_read(current_user.user_id, notification_id)}
