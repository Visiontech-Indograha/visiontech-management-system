"""
app/modules/work_plans/dependencies.py

Perakitan service modul work_plans (jadwal harian daily-first) untuk FastAPI `Depends`.
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.work_plans.repositories.daily_plan_repository import DailyPlanRepository
from app.modules.work_plans.repositories.plan_item_repository import PlanItemRepository
from app.modules.work_plans.repositories.survey_repository import SurveyRepository
from app.modules.work_plans.services.daily_plan_service import DailyPlanService
from app.modules.work_plans.services.geocode_service import GeocodeService
from app.modules.work_plans.services.plan_item_service import PlanItemService
from app.modules.work_plans.services.survey_service import SurveyService


def get_daily_plan_service(db: AsyncSession = Depends(get_db_with_user)) -> DailyPlanService:
    return DailyPlanService(db, DailyPlanRepository(db))


def get_geocode_service() -> GeocodeService:
    return GeocodeService()


def get_plan_item_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanItemService:
    return PlanItemService(db, PlanItemRepository(db))


def get_survey_service(db: AsyncSession = Depends(get_db_with_user)) -> SurveyService:
    return SurveyService(db, SurveyRepository(db))
