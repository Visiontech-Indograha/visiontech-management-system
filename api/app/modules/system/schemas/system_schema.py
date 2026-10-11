"""
app/modules/system/schemas/system_schema.py

Skema validasi permintaan dan respons fungsionalitas sistem.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.4.
"""
from app.schemas.app_release import AppUpdateOut
from app.schemas.monitoring import AttendanceRecap, TimelineGroup
from app.schemas.sync import (
    OfflineOperation,
    OperationResult,
    OperationStatus,
    SyncRequest,
    SyncResponse,
)

__all__ = [
    "AppUpdateOut",
    "AttendanceRecap",
    "OfflineOperation",
    "OperationResult",
    "OperationStatus",
    "SyncRequest",
    "SyncResponse",
    "TimelineGroup",
]
