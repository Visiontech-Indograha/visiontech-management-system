"""
Paket routing untuk modul work_plans (jadwal harian daily-first).
"""

from app.modules.work_plans.routes.daily_plan_route import router as daily_plans_router

__all__ = ["daily_plans_router"]
