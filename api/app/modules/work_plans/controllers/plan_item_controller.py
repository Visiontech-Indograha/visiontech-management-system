"""
app/modules/work_plans/controllers/plan_item_controller.py
Controller orkestrasi use case item pekerjaan per titik & rollover.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.work_plans.dependencies import get_plan_item_service
from app.modules.work_plans.schemas.plan_item_schema import (
    ChainStep,
    PlanItemCreate,
    PlanItemOut,
    PlanItemUpdate,
    PrerequisiteOption,
    ProgressIn,
    RolloverDecision,
    RolloverRequest,
)
from app.modules.work_plans.services.plan_item_service import PlanItemService


class PlanItemController:
    """Controller item pekerjaan per titik."""

    def __init__(self, service: PlanItemService = Depends(get_plan_item_service)) -> None:
        self.service = service

    @staticmethod
    def _out(row: object) -> PlanItemOut:
        return PlanItemOut(**row._mapping)  # type: ignore[attr-defined]

    async def handle_list(self, user: CurrentUser, daily_plan_id: UUID) -> list[PlanItemOut]:
        return [self._out(r) for r in await self.service.list_of_daily(user, daily_plan_id)]

    async def handle_prerequisite_options(self, user: CurrentUser, daily_plan_id: UUID) -> list[PrerequisiteOption]:
        rows = await self.service.prerequisite_options(user, daily_plan_id)
        return [PrerequisiteOption(**dict(r._mapping)) for r in rows]

    async def handle_get(self, user: CurrentUser, item_id: UUID) -> PlanItemOut:
        return self._out(await self.service.get(user, item_id))

    async def handle_create(self, user: CurrentUser, daily_plan_id: UUID, data: PlanItemCreate) -> PlanItemOut:
        return self._out(await self.service.create(user, daily_plan_id, data))

    async def handle_update(self, user: CurrentUser, item_id: UUID, data: PlanItemUpdate) -> PlanItemOut:
        return self._out(await self.service.update(user, item_id, data))

    async def handle_delete(self, user: CurrentUser, item_id: UUID) -> dict[str, str]:
        await self.service.delete(user, item_id)
        return {"message": "Item dihapus."}

    async def handle_progress(self, user: CurrentUser, item_id: UUID, data: ProgressIn) -> PlanItemOut:
        return self._out(await self.service.progress(user, item_id, data))

    async def handle_request_rollover(self, user: CurrentUser, item_id: UUID, data: RolloverRequest) -> PlanItemOut:
        return self._out(await self.service.request_rollover(user, item_id, data))

    async def handle_decide_rollover(self, user: CurrentUser, item_id: UUID, data: RolloverDecision) -> PlanItemOut:
        return self._out(await self.service.decide_rollover(user, item_id, data))

    async def handle_chain(self, user: CurrentUser, item_id: UUID) -> list[ChainStep]:
        return [ChainStep(**r._mapping) for r in await self.service.chain(user, item_id)]
