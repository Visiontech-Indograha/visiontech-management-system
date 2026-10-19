"""
app/crud/crud_notification.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.notifications.repositories.notification_repository import (
    CRUDNotification,
    NotificationRepository,
)

__all__ = ["CRUDNotification", "NotificationRepository"]
