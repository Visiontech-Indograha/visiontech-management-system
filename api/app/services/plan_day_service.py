"""
app/services/plan_day_service.py
Baca hari kerja SK beserta tugas & laporan harian. Kewenangan (melihat SK) dijaga penjaga V-07 di router.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_plan_day import CRUDPlanDay
from app.services.access_service import PlanAccess


class PlanDayService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = CRUDPlanDay(db)

    async def list_days(self, access: PlanAccess) -> list[Any]:
        return await self.repo.days_with_tasks_and_reports(access.plan.id)
