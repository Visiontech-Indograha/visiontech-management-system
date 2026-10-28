"""
Paket routing untuk modul work_plans (jadwal harian daily-first).
"""

from app.modules.work_plans.routes.daily_correction_route import router as daily_corrections_router
from app.modules.work_plans.routes.daily_plan_route import router as daily_plans_router
from app.modules.work_plans.routes.plan_item_route import router as plan_items_router
from app.modules.work_plans.routes.survey_route import router as surveys_router

__all__ = ["daily_corrections_router", "daily_plans_router", "plan_items_router", "surveys_router"]
