"""
app/modules/work_plans/schemas/work_plan_schema.py

Skema validasi permintaan dan respons modul rencana kerja (SK).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.4.
"""

from app.schemas.plan import (
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
from app.schemas.plan_attachment import AttachmentResponse, AttachmentsRequest
from app.schemas.plan_change import (
    ChangeRequest,
    ChangeResponse,
    DecisionRequest,
)
from app.schemas.plan_day import PlanDayOut
from app.schemas.plan_draft import (
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
from app.schemas.plan_location import GeoResult, PlanLocationIn, PlanLocationOut
from app.schemas.plan_member import TeamMemberOut, TeamRequest, TeamResponse
from app.schemas.plan_revision import PlanRevisionIn, PlanRevisionOut
from app.schemas.plan_transition import (
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
