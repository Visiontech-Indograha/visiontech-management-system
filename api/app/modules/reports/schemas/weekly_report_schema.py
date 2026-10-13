"""
app/modules/reports/schemas/weekly_report_schema.py

Skema validasi permintaan dan respons laporan mingguan pekerjaan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.4.
"""
from app.schemas.weekly_report import (
    WeeklyReportRequest,
    WeeklyReportResponse,
    WeeklyReviewRequest,
)

__all__ = [
    "WeeklyReportRequest",
    "WeeklyReportResponse",
    "WeeklyReviewRequest",
]
