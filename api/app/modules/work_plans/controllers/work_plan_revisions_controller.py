"""
app/modules/work_plans/controllers/work_plan_revisions_controller.py

Controller orkestrasi use case revisi rencana kerja oleh PM dan riwayatnya.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from app.api.deps import get_plan_revision_service
from app.modules.work_plans.schemas.work_plan_schema import (
    PlanDetailOut,
    PlanRevisionIn,
    PlanRevisionOut,
)
from app.modules.work_plans.services.plan_revision_service import PlanRevisionService
from app.shared.access.access_service import PlanAccess


class WorkPlanRevisionsController:
    """Controller pelaksanaan revisi draf rencana kerja oleh PM dan pembacaan riwayat revisi."""

    def __init__(
        self,
        plan_revision_service: PlanRevisionService = Depends(get_plan_revision_service),
    ) -> None:
        self.service = plan_revision_service

    async def handle_revise_plan(
        self,
        access: PlanAccess,
        data: PlanRevisionIn,
    ) -> PlanDetailOut:
        """PM merevisi rencana kerja aktif/draf dan mempublikasikan versi baru bertanda tangan."""
        return PlanDetailOut(**await self.service.revise_plan(access, data))

    async def handle_list_revisions(
        self,
        plan_id: UUID,
    ) -> list[PlanRevisionOut]:
        """Mengambil seluruh daftar riwayat revisi rencana kerja beserta ringkasan perubahannya."""
        rows = await self.service.list_revisions(plan_id)
        return [PlanRevisionOut(**r._mapping) for r in rows]


__all__ = ["WorkPlanRevisionsController"]
