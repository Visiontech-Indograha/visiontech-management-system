"""
app/crud/crud_weekly_report.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.reports.repositories.weekly_report_repository import (
    CRUDWeeklyReport,
    WeeklyReportRepository,
)

__all__ = ["CRUDWeeklyReport", "WeeklyReportRepository"]
