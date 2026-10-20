"""
app/modules/work_plans/dependencies.py

Perakitan service modul work_plans (jadwal harian daily-first) untuk FastAPI `Depends`.
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.work_plans.repositories.daily_plan_repository import DailyPlanRepository
from app.modules.work_plans.services.daily_plan_service import DailyPlanService
from app.modules.work_plans.services.geocode_service import GeocodeService


def get_daily_plan_service(db: AsyncSession = Depends(get_db_with_user)) -> DailyPlanService:
    return DailyPlanService(db, DailyPlanRepository(db))


def get_geocode_service() -> GeocodeService:
    return GeocodeService()
