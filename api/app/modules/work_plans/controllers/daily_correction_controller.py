"""
app/modules/work_plans/controllers/daily_correction_controller.py
Controller koreksi laporan harian. Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.work_plans.dependencies import get_daily_correction_service
from app.modules.work_plans.schemas.daily_correction_schema import CorrectionCreate, CorrectionDecide, CorrectionOut
from app.modules.work_plans.services.daily_correction_service import DailyCorrectionService


class DailyCorrectionController:
    """Controller koreksi laporan harian."""

    def __init__(self, service: DailyCorrectionService = Depends(get_daily_correction_service)) -> None:
        self.service = service

    async def handle_request(self, user: CurrentUser, daily_plan_id: UUID, data: CorrectionCreate) -> CorrectionOut:
        return CorrectionOut(**(await self.service.request(user, daily_plan_id, data))._mapping)

    async def handle_of_plan(self, user: CurrentUser, daily_plan_id: UUID) -> list[CorrectionOut]:
        return [CorrectionOut(**r._mapping) for r in await self.service.of_plan(user, daily_plan_id)]

    async def handle_inbox(self, user: CurrentUser, status: str | None) -> list[CorrectionOut]:
        return [CorrectionOut(**r._mapping) for r in await self.service.inbox(user, status)]

    async def handle_decide(self, user: CurrentUser, correction_id: UUID, data: CorrectionDecide) -> CorrectionOut:
        return CorrectionOut(**(await self.service.decide(user, correction_id, data))._mapping)

    async def handle_submit(self, user: CurrentUser, correction_id: UUID) -> CorrectionOut:
        return CorrectionOut(**(await self.service.submit_revision(user, correction_id))._mapping)
