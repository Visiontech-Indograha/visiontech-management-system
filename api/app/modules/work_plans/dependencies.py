"""
app/modules/work_plans/dependencies.py

Perakitan service modul work_plans untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.work_plans.repositories.plan_assignment_repository import CRUDPlanAssignment
from app.modules.work_plans.repositories.plan_member_repository import CRUDPlanMember
from app.modules.work_plans.repositories.plan_transition_repository import CRUDPlanTransition
from app.modules.work_plans.services.member_report_service import MemberReportService
from app.modules.work_plans.services.plan_amendment_service import PlanAmendmentService
from app.modules.work_plans.services.plan_assignment_service import PlanAssignmentService
from app.modules.work_plans.services.plan_attachment_service import PlanAttachmentService
from app.modules.work_plans.services.plan_change_service import PlanChangeService
from app.modules.work_plans.services.plan_day_service import PlanDayService
from app.modules.work_plans.services.plan_draft_service import PlanDraftService
from app.modules.work_plans.services.plan_edit_service import PlanEditService
from app.modules.work_plans.services.plan_item_service import PlanItemService
from app.modules.work_plans.services.plan_location_service import PlanLocationService
from app.modules.work_plans.services.plan_member_service import PlanMemberService
from app.modules.work_plans.services.plan_revision_service import PlanRevisionService
from app.modules.work_plans.services.plan_transition_service import PlanTransitionService


def get_plan_assignment_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanAssignmentService:
    return PlanAssignmentService(CRUDPlanAssignment(db))


def get_plan_attachment_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanAttachmentService:
    return PlanAttachmentService(db)


def get_plan_change_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanChangeService:
    return PlanChangeService(db)


def get_plan_day_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanDayService:
    return PlanDayService(db)


def get_plan_amendment_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanAmendmentService:
    return PlanAmendmentService(db)


def get_plan_revision_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanRevisionService:
    return PlanRevisionService(db)


def get_plan_draft_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanDraftService:
    return PlanDraftService(db)


def get_member_report_service(db: AsyncSession = Depends(get_db_with_user)) -> MemberReportService:
    return MemberReportService(db)


def get_plan_edit_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanEditService:
    return PlanEditService(db, PlanAssignmentService(CRUDPlanAssignment(db)))


def get_plan_item_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanItemService:
    return PlanItemService(db)


def get_plan_location_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanLocationService:
    return PlanLocationService(db)


def get_plan_member_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanMemberService:
    return PlanMemberService(CRUDPlanMember(db))


def get_plan_transition_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanTransitionService:
    return PlanTransitionService(CRUDPlanTransition(db), CRUDPlanMember(db))
