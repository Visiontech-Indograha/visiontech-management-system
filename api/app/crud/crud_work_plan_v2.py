"""
api/app/crud/crud_work_plan_v2.py

Shim re-export untuk kompatibilitas. Implementasi riil berada di:
app.modules.work_plans.repositories.work_plan_v2_repository.
"""

from app.modules.work_plans.repositories.work_plan_v2_repository import (
    CRUDWorkPlanV2,
    WorkPlanV2Repository,
)

__all__ = ["CRUDWorkPlanV2", "WorkPlanV2Repository"]
