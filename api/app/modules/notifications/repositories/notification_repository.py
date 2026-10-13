"""
app/modules/notifications/repositories/notification_repository.py

Repositori data notifikasi pengguna.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.5.
"""
from app.crud.crud_notification import CRUDNotification


class NotificationRepository(CRUDNotification):
    """
    Repositori akses data notifikasi pengguna.
    """


__all__ = ["NotificationRepository"]

