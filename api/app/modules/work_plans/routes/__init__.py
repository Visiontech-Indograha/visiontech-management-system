"""
Paket routing untuk modul work_plans.
"""
from app.modules.work_plans.routes.work_plan_amendments_route import (
    router as plan_amendments_router,
)
from app.modules.work_plans.routes.work_plan_attachments_route import (
    router as plan_attachments_router,
)
from app.modules.work_plans.routes.work_plan_changes_route import (
    plan_router as plan_changes_router,
)
from app.modules.work_plans.routes.work_plan_changes_route import (
    router as changes_router,
)
from app.modules.work_plans.routes.work_plan_days_route import (
    router as plan_days_router,
)
from app.modules.work_plans.routes.work_plan_location_route import (
    router as plan_location_router,
)
from app.modules.work_plans.routes.work_plan_members_route import (
    router as plan_members_router,
)
from app.modules.work_plans.routes.work_plan_reports_route import (
    router as plan_reports_router,
)
from app.modules.work_plans.routes.work_plan_revisions_route import (
    router as plan_revisions_router,
)
from app.modules.work_plans.routes.work_plan_transitions_route import (
    router as transitions_router,
)
from app.modules.work_plans.routes.work_plans_route import (
    router as plans_router,
)

__all__ = [
    "changes_router",
    "plan_amendments_router",
    "plan_attachments_router",
    "plan_changes_router",
    "plan_days_router",
    "plan_location_router",
    "plan_members_router",
    "plan_reports_router",
    "plan_revisions_router",
    "plans_router",
    "transitions_router",
]

