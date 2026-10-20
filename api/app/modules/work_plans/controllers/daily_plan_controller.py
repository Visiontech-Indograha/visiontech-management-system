"""
app/modules/work_plans/controllers/daily_plan_controller.py
Controller orkestrasi use case jadwal harian daily-first.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.work_plans.dependencies import get_daily_plan_service, get_geocode_service
from app.modules.work_plans.schemas.daily_plan_schema import (
    BulkApproveOut,
    DailyFormOptions,
    DailyPlanCreate,
    DailyPlanDetail,
    DailyPlanOut,
    DailyPlanUpdate,
    GeoResult,
)
from app.modules.work_plans.services.daily_plan_service import DailyPlanService
from app.modules.work_plans.services.geocode_service import GeocodeService


class DailyPlanController:
    """Controller jadwal harian, matriks persetujuan, dan pencarian lokasi."""

    def __init__(
        self,
        service: DailyPlanService = Depends(get_daily_plan_service),
        geocoder: GeocodeService = Depends(get_geocode_service),
    ) -> None:
        self.service = service
        self.geocoder = geocoder

    @staticmethod
    def _out(row: object) -> DailyPlanOut:
        return DailyPlanOut(**row._mapping)  # type: ignore[attr-defined]

    async def handle_list(
        self, user: CurrentUser, start: date | None, end: date | None, division_id: UUID | None,
        team_id: UUID | None, status: str | None,
    ) -> list[DailyPlanOut]:
        rows = await self.service.list_plans(user, start=start, end=end, division_id=division_id, team_id=team_id,
                                             status=status)
        return [self._out(r) for r in rows]

    async def handle_detail(self, daily_plan_id: UUID) -> DailyPlanDetail:
        return DailyPlanDetail(**await self.service.detail(daily_plan_id))

    async def handle_form_options(self, user: CurrentUser) -> DailyFormOptions:
        return DailyFormOptions(**await self.service.form_options(user))

    async def handle_order_schedule(self, user: CurrentUser, completion_id: UUID) -> list[DailyPlanOut]:
        return [self._out(r) for r in await self.service.plans_of_order(user, completion_id)]

    async def handle_create(self, user: CurrentUser, data: DailyPlanCreate) -> DailyPlanOut:
        return self._out(await self.service.create(user, data))

    async def handle_update(self, user: CurrentUser, daily_plan_id: UUID, data: DailyPlanUpdate) -> DailyPlanOut:
        return self._out(await self.service.update(user, daily_plan_id, data))

    async def handle_copy(self, user: CurrentUser, daily_plan_id: UUID, work_dates: list[date]) -> list[DailyPlanOut]:
        return [self._out(r) for r in await self.service.copy(user, daily_plan_id, work_dates)]

    async def handle_delete(self, user: CurrentUser, daily_plan_id: UUID) -> dict[str, str]:
        await self.service.delete(user, daily_plan_id)
        return {"message": "Jadwal harian dihapus."}

    async def handle_attachments(self, user: CurrentUser, daily_plan_id: UUID, file_ids: list[UUID]) -> list[UUID]:
        return await self.service.set_attachments(user, daily_plan_id, file_ids)

    async def handle_transition(self, user: CurrentUser, daily_plan_id: UUID, action: str,
                                reason: str | None = None) -> DailyPlanOut:
        if action == "reject":
            return self._out(await self.service.reject(user, daily_plan_id, reason or ""))
        handler = {"submit": self.service.submit, "approve": self.service.approve,
                   "start": self.service.start, "complete": self.service.complete}[action]
        return self._out(await handler(user, daily_plan_id))

    async def handle_bulk_approve(self, user: CurrentUser, daily_plan_ids: list[UUID]) -> BulkApproveOut:
        return BulkApproveOut(**await self.service.bulk_approve(user, daily_plan_ids))

    async def handle_geo_search(self, q: str) -> list[GeoResult]:
        return [GeoResult(**r) for r in await self.geocoder.search(q)]
