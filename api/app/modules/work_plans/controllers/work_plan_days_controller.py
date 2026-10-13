"""
app/modules/work_plans/controllers/work_plan_days_controller.py

Controller orkestrasi use case pembacaan hari kerja dan tugas harian SK.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends

from app.api.deps import get_plan_day_service
from app.modules.work_plans.schemas.work_plan_schema import PlanDayOut
from app.modules.work_plans.services.work_plan_service import PlanDayService
from app.services.access_service import PlanAccess


def _out(row: Any) -> PlanDayOut:
    """Fungsi pembantu memetakan baris database ke skema PlanDayOut."""
    return PlanDayOut(**(row if isinstance(row, dict) else row._mapping))


class WorkPlanDaysController:
    """Controller pembacaan jadwal hari penugasan dan laporan harian per hari."""

    def __init__(
        self,
        plan_day_service: PlanDayService = Depends(get_plan_day_service),
    ) -> None:
        self.service = plan_day_service

    async def handle_list_days(
        self,
        access: PlanAccess,
    ) -> list[PlanDayOut]:
        """Mengambil daftar hari kerja, tugas, dan status laporan harian rencana kerja."""
        return [_out(row) for row in await self.service.list_days(access)]


__all__ = ["WorkPlanDaysController"]

