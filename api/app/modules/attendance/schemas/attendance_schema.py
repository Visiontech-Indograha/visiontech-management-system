"""
app/modules/attendance/schemas/attendance_schema.py

Skema validasi permintaan dan respons absensi lapangan, luring, dan pemantauan cron.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.4.
"""

from app.schemas.attendance import (
    AttendanceChannel,
    AttendanceListResponse,
    AttendanceResponse,
    CheckInRequest,
    CheckOutRequest,
    DeviceKeyRequest,
    ExplanationRequest,
    GeoPoint,
    MissingCheckInResponse,
    NeedsReviewResponse,
    OfflineAttendanceEvent,
    OfflineAttendanceResult,
    ReviewRequest,
    SiteCreate,
    SiteResponse,
)

__all__ = [
    "AttendanceChannel",
    "AttendanceListResponse",
    "AttendanceResponse",
    "CheckInRequest",
    "CheckOutRequest",
    "DeviceKeyRequest",
    "ExplanationRequest",
    "GeoPoint",
    "MissingCheckInResponse",
    "NeedsReviewResponse",
    "OfflineAttendanceEvent",
    "OfflineAttendanceResult",
    "ReviewRequest",
    "SiteCreate",
    "SiteResponse",
]
