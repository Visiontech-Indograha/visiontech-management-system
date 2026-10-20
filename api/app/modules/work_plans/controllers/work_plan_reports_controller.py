"""
app/modules/work_plans/controllers/work_plan_reports_controller.py

Controller orkestrasi use case laporan harian berjenjang anggota dan dokumen laporan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from fastapi.responses import HTMLResponse

from app.api.deps import get_member_report_service
from app.modules.work_plans.schemas.work_plan_schema import (
    MemberReportIn,
    MemberReportOut,
)
from app.modules.work_plans.services.member_report_service import MemberReportService
from app.shared.access.access_service import PlanAccess


class WorkPlanReportsController:
    """Controller pengisian, pengiriman laporan harian anggota tim, dan render dokumen A4 laporan."""

    def __init__(
        self,
        member_report_service: MemberReportService = Depends(get_member_report_service),
    ) -> None:
        self.service = member_report_service

    async def handle_member_reports(
        self,
        day_id: UUID,
    ) -> list[MemberReportOut]:
        """Mengambil seluruh laporan anggota untuk satu hari tertentu."""
        rows = await self.service.list_for_day(day_id)
        return [MemberReportOut(**r._mapping) for r in rows]

    async def handle_my_member_report(
        self,
        access: PlanAccess,
        day_id: UUID,
    ) -> MemberReportOut | None:
        """Mengambil draf laporan harian milik anggota sendiri pada hari tertentu."""
        row = await self.service.mine(access, day_id)
        return MemberReportOut(**row._mapping) if row else None

    async def handle_save_member_report(
        self,
        access: PlanAccess,
        day_id: UUID,
        data: MemberReportIn,
    ) -> MemberReportOut:
        """Menyimpan atau memperbarui draf laporan kerja harian anggota."""
        row = await self.service.save(
            access,
            day_id,
            data.body,
            data.obstacle,
            data.evidence_file_ids,
            data.evidence,
        )
        return MemberReportOut(**row._mapping)

    async def handle_send_member_report(
        self,
        access: PlanAccess,
        day_id: UUID,
    ) -> MemberReportOut:
        """Mengirimkan laporan harian anggota kepada ketua tim untuk ditinjau."""
        row = await self.service.send(access, day_id)
        return MemberReportOut(**row._mapping)

    async def handle_daily_report_html(
        self,
        access: PlanAccess,
        day_id: UUID,
    ) -> HTMLResponse:
        """Menghasilkan representasi HTML format cetak A4 laporan harian."""
        return HTMLResponse(await self.service.daily_report_html(access, day_id))

    async def handle_weekly_report_html(
        self,
        access: PlanAccess,
        week: int,
    ) -> HTMLResponse:
        """Menghasilkan representasi HTML format cetak A4 laporan mingguan."""
        return HTMLResponse(await self.service.weekly_report_html(access, f"Laporan Mingguan {week}"))


__all__ = ["WorkPlanReportsController"]
