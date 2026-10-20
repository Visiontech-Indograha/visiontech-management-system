"""
app/modules/work_plans/services/work_plan_v2_service.py

Logika bisnis Rencana Kerja V2 (form options, matriks mingguan, jadwal proyek, CRUD mingguan/harian/butir tugas).
Data dibaca/ditulis lewat CRUDWorkPlanV2; service menegakkan aturan "tidak ditemukan" dan resolusi pembuat.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from app.core.errors import NotFoundError
from app.core.security import CurrentUser
from app.modules.work_plans.repositories.work_plan_v2_repository import CRUDWorkPlanV2
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


class WorkPlanV2Service:
    """Layanan Rencana Kerja V2 terintegrasi (Master Schema V2)."""

    def __init__(self, repo: CRUDWorkPlanV2) -> None:
        self.repo = repo

    async def form_options(self) -> WorkPlanFormOptionsV2Out:
        return await self.repo.get_form_options_v2()

    async def weekly_matrix(
        self, start_date: date, end_date: date, division_id: UUID | None, team_id: UUID | None
    ) -> WeeklyCalendarMatrixOut:
        return await self.repo.get_weekly_matrix(
            start_date=start_date, end_date=end_date, division_id=division_id, team_id=team_id
        )

    async def bulk_approve(self, user: CurrentUser, payload: BulkApproveDailyPlansIn) -> BulkApproveDailyPlansOut:
        pm_id = user.employee_id or await self.repo.get_creator_employee_id(user.user_id)
        return await self.repo.bulk_approve_days(
            pm_employee_id=UUID(str(pm_id)),
            start_date=payload.start_date,
            end_date=payload.end_date,
            team_id=payload.team_id,
        )

    async def project_schedule(self, completion_id: UUID) -> ProjectScheduleOut:
        schedule = await self.repo.get_project_schedule(completion_id)
        if not schedule:
            raise NotFoundError("Data proyek work completion tidak ditemukan.")
        return schedule

    # ── Rencana mingguan ─────────────────────────────────────────

    async def list_weekly(
        self,
        status_filter: str | None,
        division_id: UUID | None,
        team_id: UUID | None,
        year: int | None,
        limit: int,
    ) -> list[WeeklyPlanListOut]:
        return await self.repo.list_weekly_plans(
            status_filter=status_filter, division_id=division_id, team_id=team_id, year=year, limit=limit
        )

    async def weekly_detail(self, weekly_plan_id: UUID) -> WeeklyPlanDetailOut:
        plan = await self.repo.get_weekly_plan_detail(weekly_plan_id)
        if not plan:
            raise NotFoundError("Rencana kerja mingguan tidak ditemukan.")
        return plan

    async def create_weekly(self, user: CurrentUser, payload: WeeklyPlanCreateIn) -> WeeklyPlanDetailOut:
        creator_id = await self.repo.get_creator_employee_id(user.user_id)
        return await self.repo.create_weekly_plan(creator_id, payload)

    async def update_weekly(self, weekly_plan_id: UUID, payload: WeeklyPlanUpdateIn) -> WeeklyPlanDetailOut:
        plan = await self.repo.update_weekly_plan(weekly_plan_id, payload)
        if not plan:
            raise NotFoundError("Rencana kerja mingguan tidak ditemukan.")
        return plan

    async def delete_weekly(self, weekly_plan_id: UUID) -> None:
        if not await self.repo.delete_weekly_plan(weekly_plan_id):
            raise NotFoundError("Rencana kerja mingguan tidak ditemukan atau telah dihapus.")

    # ── Hari kerja ───────────────────────────────────────────────

    async def daily(self, daily_plan_id: UUID) -> DailyPlanOut:
        day = await self.repo.get_daily_plan(daily_plan_id)
        if not day:
            raise NotFoundError("Hari kerja tidak ditemukan.")
        return day

    async def create_daily(self, user: CurrentUser, payload: DailyPlanCreateIn) -> DailyPlanOut:
        creator_id = await self.repo.get_creator_employee_id(user.user_id)
        return await self.repo.create_daily_plan(payload, creator_id)

    async def update_daily(self, daily_plan_id: UUID, payload: DailyPlanUpdateIn) -> DailyPlanOut:
        day = await self.repo.update_daily_plan(daily_plan_id, payload)
        if not day:
            raise NotFoundError("Hari kerja tidak ditemukan.")
        return day

    async def delete_daily(self, daily_plan_id: UUID) -> None:
        if not await self.repo.delete_daily_plan(daily_plan_id):
            raise NotFoundError("Hari kerja tidak ditemukan atau telah dihapus.")

    # ── Butir tugas ──────────────────────────────────────────────

    async def item(self, item_id: UUID) -> PlanItemOut:
        item = await self.repo.get_plan_item(item_id)
        if not item:
            raise NotFoundError("Butir tugas tidak ditemukan.")
        return item

    async def create_item(self, payload: PlanItemCreateIn) -> PlanItemOut:
        return await self.repo.create_plan_item(payload)

    async def update_item(self, item_id: UUID, payload: PlanItemUpdateIn) -> PlanItemOut:
        item = await self.repo.update_plan_item(item_id, payload)
        if not item:
            raise NotFoundError("Butir tugas tidak ditemukan.")
        return item

    async def delete_item(self, item_id: UUID) -> None:
        if not await self.repo.delete_plan_item(item_id):
            raise NotFoundError("Butir tugas tidak ditemukan atau telah dihapus.")
