"""
app/modules/hse/schemas/hse_schema.py

Skema validasi permintaan dan respons insiden K3 (HSE) dan laporan harian.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.4.
"""
from app.schemas.hse import (
    DailyReportCreate,
    DailyReportResponse,
    IncidentCreate,
    IncidentResolve,
    IncidentResponse,
    ReportReviewRequest,
)

__all__ = [
    "DailyReportCreate",
    "DailyReportResponse",
    "IncidentCreate",
    "IncidentResolve",
    "IncidentResponse",
    "ReportReviewRequest",
]
