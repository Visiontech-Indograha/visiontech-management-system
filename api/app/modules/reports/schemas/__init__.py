"""
Paket skema untuk modul reports.
"""

from app.modules.reports.schemas.weekly_report_schema import (
    WeeklyReportRequest,
    WeeklyReportResponse,
    WeeklyReviewRequest,
)

__all__ = [
    "WeeklyReportRequest",
    "WeeklyReportResponse",
    "WeeklyReviewRequest",
]
