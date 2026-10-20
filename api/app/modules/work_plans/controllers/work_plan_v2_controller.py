"""
app/modules/work_plans/controllers/work_plan_v2_controller.py

Controller orkestrasi use case Rencana Kerja V2 (form options, matriks, jadwal proyek, CRUD mingguan/harian/tugas).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.work_plans.dependencies import get_work_plan_v2_service
from app.modules.work_plans.schemas.work_plan_v2_schema import (
    BulkApproveDailyPlansIn,
    BulkApproveDailyPlansOut,
    DailyPlanCreateIn,
    DailyPlanOut,
    DailyPlanUpdateIn,
    PlanItemCreateIn,
    PlanItemOut,
    PlanItemUpdateIn,
    ProjectScheduleOut,
    WeeklyCalendarMatrixOut,
    WeeklyPlanCreateIn,
    WeeklyPlanDetailOut,
    WeeklyPlanListOut,
    WeeklyPlanUpdateIn,
    WorkPlanFormOptionsV2Out,
)
from app.modules.work_plans.services.work_plan_v2_service import WorkPlanV2Service


class WorkPlanV2Controller:
    """Controller Rencana Kerja V2."""

    def __init__(self, service: WorkPlanV2Service = Depends(get_work_plan_v2_service)) -> None:
        self.service = service

    async def handle_form_options(self) -> WorkPlanFormOptionsV2Out:
        return await self.service.form_options()

    async def handle_weekly_matrix(
        self, start_date: date, end_date: date, division_id: UUID | None, team_id: UUID | None
    ) -> WeeklyCalendarMatrixOut:
        return await self.service.weekly_matrix(start_date, end_date, division_id, team_id)

    async def handle_bulk_approve(
        self, user: CurrentUser, payload: BulkApproveDailyPlansIn
    ) -> BulkApproveDailyPlansOut:
        return await self.service.bulk_approve(user, payload)

    async def handle_project_schedule(self, completion_id: UUID) -> ProjectScheduleOut:
        return await self.service.project_schedule(completion_id)

    async def handle_list_weekly(
        self,
        status_filter: str | None,
        division_id: UUID | None,
        team_id: UUID | None,
        year: int | None,
        limit: int,
    ) -> list[WeeklyPlanListOut]:
        return await self.service.list_weekly(status_filter, division_id, team_id, year, limit)

    async def handle_weekly_detail(self, weekly_plan_id: UUID) -> WeeklyPlanDetailOut:
        return await self.service.weekly_detail(weekly_plan_id)

    async def handle_create_weekly(self, user: CurrentUser, payload: WeeklyPlanCreateIn) -> WeeklyPlanDetailOut:
        return await self.service.create_weekly(user, payload)

    async def handle_update_weekly(self, weekly_plan_id: UUID, payload: WeeklyPlanUpdateIn) -> WeeklyPlanDetailOut:
        return await self.service.update_weekly(weekly_plan_id, payload)

    async def handle_delete_weekly(self, weekly_plan_id: UUID) -> dict[str, str]:
        await self.service.delete_weekly(weekly_plan_id)
        return {"message": "Rencana kerja mingguan berhasil dihapus."}

    async def handle_daily(self, daily_plan_id: UUID) -> DailyPlanOut:
        return await self.service.daily(daily_plan_id)

    async def handle_create_daily(self, user: CurrentUser, payload: DailyPlanCreateIn) -> DailyPlanOut:
        return await self.service.create_daily(user, payload)

    async def handle_update_daily(self, daily_plan_id: UUID, payload: DailyPlanUpdateIn) -> DailyPlanOut:
        return await self.service.update_daily(daily_plan_id, payload)

    async def handle_delete_daily(self, daily_plan_id: UUID) -> dict[str, str]:
        await self.service.delete_daily(daily_plan_id)
        return {"message": "Hari kerja berhasil dihapus."}

    async def handle_item(self, item_id: UUID) -> PlanItemOut:
        return await self.service.item(item_id)

    async def handle_create_item(self, payload: PlanItemCreateIn) -> PlanItemOut:
        return await self.service.create_item(payload)

    async def handle_update_item(self, item_id: UUID, payload: PlanItemUpdateIn) -> PlanItemOut:
        return await self.service.update_item(item_id, payload)

    async def handle_delete_item(self, item_id: UUID) -> dict[str, str]:
        await self.service.delete_item(item_id)
        return {"message": "Butir tugas berhasil dihapus."}


__all__ = ["WorkPlanV2Controller"]
