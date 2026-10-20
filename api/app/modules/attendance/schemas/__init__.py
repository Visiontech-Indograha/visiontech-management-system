"""
Paket skema untuk modul attendance.
"""

from app.modules.attendance.schemas.attendance_schema import (
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
]
