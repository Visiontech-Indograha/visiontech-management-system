"""
app/modules/reports/controllers/weekly_report_controller.py

Controller orkestrasi use case laporan mingguan SK.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends

from app.api.deps import get_weekly_report_service
from app.modules.reports.schemas.weekly_report_schema import (
    WeeklyReportRequest,
    WeeklyReportResponse,
    WeeklyReviewRequest,
)
from app.modules.reports.services.weekly_report_service import WeeklyReportService
from app.services.access_service import PlanAccess


def _out(row: Any) -> WeeklyReportResponse:
    """Memetakan row laporan mingguan dari database ke skema WeeklyReportResponse."""
    return WeeklyReportResponse(**(row if isinstance(row, dict) else row._mapping))


class WeeklyReportController:
    """
    Controller use case laporan mingguan pelaksanaan SK (pengisian, penyerahan, dan peninjauan).
    """

    def __init__(
        self,
        weekly_report_service: WeeklyReportService = Depends(get_weekly_report_service),
    ) -> None:
        self.service = weekly_report_service

    async def handle_list_weeks(self, access: PlanAccess) -> list[WeeklyReportResponse]:
        """Mengambil daftar laporan mingguan untuk sebuah SK."""
        rows = await self.service.list_weeks(access)
        return [_out(r) for r in rows]

    async def handle_save_weekly(
        self, access: PlanAccess, week: int, data: WeeklyReportRequest
    ) -> WeeklyReportResponse:
        """Menyimpan draft laporan mingguan."""
        row = await self.service.save_weekly(access, week, data.body, data.obstacle)
        return _out(row)

    async def handle_submit_weekly(self, access: PlanAccess, week: int) -> WeeklyReportResponse:
        """Mengajukan laporan mingguan agar dapat ditinjau oleh PM."""
        row = await self.service.submit_weekly(access, week)
        return _out(row)

    async def handle_review_weekly(
        self, access: PlanAccess, week: int, data: WeeklyReviewRequest
    ) -> WeeklyReportResponse:
        """Meninjau dan menyetujui atau menolak laporan mingguan."""
        row = await self.service.review_weekly(access, week, data.decision, data.note)
        return _out(row)
