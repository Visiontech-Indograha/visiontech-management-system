"""
app/modules/work_plans/schemas/work_plan_schema.py

Skema validasi permintaan dan respons modul rencana kerja (SK).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.4.
"""

from app.modules.work_plans.schemas.plan_attachment_schema import AttachmentResponse, AttachmentsRequest
from app.modules.work_plans.schemas.plan_change_schema import (
    ChangeRequest,
    ChangeResponse,
    DecisionRequest,
)
from app.modules.work_plans.schemas.plan_day_schema import PlanDailyScheduleDetailOut, PlanDayOut
from app.modules.work_plans.schemas.plan_draft_schema import (
    AmendmentReasonIn,
    FormAsset,
    FormPerson,
    FormSite,
    MemberReportIn,
    MemberReportOut,
    PlanChangeOut,
    PlanDetailOut,
    PlanDraftRequest,
    PlanFormOptions,
)
from app.modules.work_plans.schemas.plan_location_schema import GeoResult, PlanLocationIn, PlanLocationOut
from app.modules.work_plans.schemas.plan_member_schema import TeamMemberOut, TeamRequest, TeamResponse
from app.modules.work_plans.schemas.plan_revision_schema import PlanRevisionIn, PlanRevisionOut
from app.modules.work_plans.schemas.plan_schema import (
    AssignmentEmployeeOption,
    DayPlanRequest,
    PlanAssignmentOptions,
    PlanDayCreate,
    PlanDayResponse,
    PlanTaskCreate,
    PlanTaskResponse,
    RescheduleItemRequest,
    RescheduleItemResponse,
    WorkPlanCreate,
    WorkPlanResponse,
    WorkPlanUpdate,
)
from app.modules.work_plans.schemas.plan_transition_schema import (
    CompletionRequest,
    FinalReportOut,
    FinalReportSignatureOut,
    TransitionRequest,
)

__all__ = [
    "AmendmentReasonIn",
    "AssignmentEmployeeOption",
    "AttachmentResponse",
    "AttachmentsRequest",
    "ChangeRequest",
    "ChangeResponse",
    "CompletionRequest",
    "DayPlanRequest",
    "DecisionRequest",
    "FinalReportOut",
    "FinalReportSignatureOut",
    "FormAsset",
    "FormPerson",
    "FormSite",
    "GeoResult",
    "MemberReportIn",
    "MemberReportOut",
    "PlanAssignmentOptions",
    "PlanChangeOut",
    "PlanDailyScheduleDetailOut",
    "PlanDayCreate",
    "PlanDayOut",
    "PlanDayResponse",
    "PlanDetailOut",
    "PlanDraftRequest",
    "PlanFormOptions",
    "PlanLocationIn",
    "PlanLocationOut",
    "PlanRevisionIn",
    "PlanRevisionOut",
    "PlanTaskCreate",
    "PlanTaskResponse",
    "RescheduleItemRequest",
    "RescheduleItemResponse",
    "TeamMemberOut",
    "TeamRequest",
    "TeamResponse",
    "TransitionRequest",
    "WorkPlanCreate",
    "WorkPlanResponse",
    "WorkPlanUpdate",
]
