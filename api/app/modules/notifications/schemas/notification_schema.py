"""
app/modules/notifications/schemas/notification_schema.py

Skema validasi permintaan dan respons notifikasi pengguna.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.4.
"""

from app.modules.work_plans.schemas.plan_draft_schema import NotificationList, NotificationOut

__all__ = ["NotificationList", "NotificationOut"]
