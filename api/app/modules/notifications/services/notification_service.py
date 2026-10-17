"""
app/modules/notifications/services/notification_service.py

Layanan logika bisnis untuk modul notifikasi pengguna.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.3.
"""

from app.services.notification_service import (
    NotificationService as BaseNotificationService,
)
from app.services.notification_service import (
    diff_summary,
)


class NotificationService(BaseNotificationService):
    """
    Layanan bisnis notifikasi pengguna.
    """


__all__ = ["NotificationService", "diff_summary"]
