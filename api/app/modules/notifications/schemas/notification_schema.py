"""
app/modules/notifications/schemas/notification_schema.py

Skema validasi permintaan dan respons notifikasi pengguna.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.4.
"""
from app.schemas.plan_draft import NotificationList, NotificationOut

__all__ = ["NotificationList", "NotificationOut"]
