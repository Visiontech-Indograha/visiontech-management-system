"""
app/services/plan_day_service.py
Baca hari kerja SK beserta tugas & laporan harian. Kewenangan (melihat SK) dijaga penjaga V-07 di router.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.guards import PlanAccess
from app.repositories.plan_day_repo import PlanDayRepo


class PlanDayService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = PlanDayRepo(db)

    async def list_days(self, access: PlanAccess) -> list[Any]:
        return await self.repo.days_with_tasks_and_reports(access.plan.id)
