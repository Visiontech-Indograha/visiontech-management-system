"""
app/modules/work_plans/routes/work_plan_attachments_route.py

Rute endpoint HTTP untuk berkas lampiran pendukung SK (/work-plans/{plan_id}/attachments).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from fastapi import APIRouter, Depends

from app.api.deps import plan_access
from app.modules.work_plans.controllers.work_plan_attachments_controller import (
    WorkPlanAttachmentsController,
)
from app.modules.work_plans.schemas.work_plan_schema import (
    AttachmentResponse,
    AttachmentsRequest,
)
from app.shared.access.access_service import PlanAccess, PlanNeed

router = APIRouter(prefix="/work-plans/{plan_id}/attachments", tags=["Work Plans"])
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))


@router.get("", response_model=list[AttachmentResponse])
async def list_attachments(
    access: PlanAccess = _VIEW_ACCESS,
    controller: WorkPlanAttachmentsController = Depends(),
) -> list[AttachmentResponse]:
    """Mengambil daftar lampiran dari sebuah SK (GET)."""
    return await controller.handle_list_attachments(access)


@router.put("", response_model=list[AttachmentResponse])
async def save_attachments(
    data: AttachmentsRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    controller: WorkPlanAttachmentsController = Depends(),
) -> list[AttachmentResponse]:
    """Menyimpan atau memperbarui lampiran untuk SK (PUT)."""
    return await controller.handle_save_attachments(access, data)


__all__ = ["router"]
