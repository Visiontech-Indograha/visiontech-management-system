"""
app/modules/hse/controllers/hse_controller.py

Controller orkestrasi use case insiden K3 dan laporan harian tim kerja.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from app.api.deps import get_hse_service
from app.core.security import CurrentUser
from app.modules.hse.schemas.hse_schema import (
    DailyReportCreate,
    DailyReportResponse,
    IncidentCreate,
    IncidentResolve,
    IncidentResponse,
    ReportReviewRequest,
)
from app.modules.hse.services.hse_service import HseService
from app.shared.access.access_service import PlanAccess


class HseController:
    """
    Controller use case insiden K3 (HSE) dan siklus laporan harian pelaksanaan SK.
    """

    def __init__(self, hse_service: HseService = Depends(get_hse_service)) -> None:
        self.hse = hse_service

    async def handle_list_incidents(self, current_user: CurrentUser, plan_id: UUID) -> list[IncidentResponse]:
        """Mengambil daftar insiden untuk satu work plan."""
        rows = await self.hse.list_incidents(current_user, plan_id)
        return [IncidentResponse(**r._mapping) for r in rows]

    async def handle_report_incident(self, current_user: CurrentUser, data: IncidentCreate) -> IncidentResponse:
        """Melaporkan insiden K3 baru pada work plan yang sedang berlangsung."""
        incident = await self.hse.report_incident(
            current_user,
            data.work_plan_id,
            data.category,
            data.severity,
            data.description,
            data.evidence_file_ids,
        )
        return IncidentResponse(**incident._mapping)

    async def handle_resolve_incident(
        self, access: PlanAccess, inc_id: UUID, data: IncidentResolve
    ) -> IncidentResponse:
        """Menyelesaikan status insiden K3."""
        row = await self.hse.resolve_incident(access, inc_id, data.resolution_note)
        return IncidentResponse(**row._mapping)

    async def handle_upsert_daily_report(
        self, access: PlanAccess, day_id: UUID, data: DailyReportCreate
    ) -> DailyReportResponse:
        """Menyimpan atau memperbarui draft laporan harian pekerjaan."""
        report = await self.hse.save_daily_report(
            access,
            day_id,
            data.body,
            data.obstacle,
            data.evidence_file_ids,
            data.evidence,
        )
        return DailyReportResponse(**report._mapping)

    async def handle_submit_daily_report(self, access: PlanAccess, day_id: UUID) -> DailyReportResponse:
        """Menyerahkan laporan harian untuk ditinjau oleh PM."""
        report = await self.hse.submit_daily_report(access, day_id)
        return DailyReportResponse(**report._mapping)

    async def handle_review_daily_report(
        self, access: PlanAccess, day_id: UUID, data: ReportReviewRequest
    ) -> DailyReportResponse:
        """Meninjau dan menyetujui atau mengembalikan laporan harian."""
        report = await self.hse.review_daily_report(access, day_id, data.decision, data.note)
        return DailyReportResponse(**report._mapping)

    async def handle_toggle_task(self, access: PlanAccess, day_id: UUID, task_id: UUID) -> dict[str, object]:
        """Mengubah centang status penyelesaian tugas harian."""
        row = await self.hse.toggle_task(access, day_id, task_id)
        return {"id": str(row.id), "is_done": row.is_done}
