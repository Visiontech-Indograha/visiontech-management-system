"""
app/modules/work_plans/routes/work_plan_amendments_route.py

Rute endpoint HTTP untuk adendum saat SK berjalan dan laporan akhir (/work-plans/{plan_id}).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.api.deps import plan_access
from app.modules.work_plans.controllers.work_plan_amendments_controller import (
    WorkPlanAmendmentsController,
)
from app.modules.work_plans.schemas.work_plan_schema import (
    AmendmentReasonIn,
    PlanChangeOut,
    PlanDetailOut,
    PlanDraftRequest,
)
from app.shared.access.access_service import PlanAccess, PlanNeed

router = APIRouter(prefix="/work-plans/{plan_id}", tags=["Work Plan Amendments"])
_VIEW = Depends(plan_access(PlanNeed.VIEW))
_LEADER = Depends(plan_access(PlanNeed.LEADER))
_PM_UNIT = Depends(plan_access(PlanNeed.PM_UNIT))


@router.get("/changes", response_model=list[PlanChangeOut])
async def list_changes(
    plan_id: UUID,
    access: PlanAccess = _VIEW,
    controller: WorkPlanAmendmentsController = Depends(),
) -> list[PlanChangeOut]:
    """Melihat riwayat usulan perubahan SK (GET)."""
    return await controller.handle_list_changes(plan_id)


@router.post("/amendments", response_model=list[PlanChangeOut])
async def request_amendment(
    plan_id: UUID,
    data: AmendmentReasonIn,
    access: PlanAccess = _LEADER,
    controller: WorkPlanAmendmentsController = Depends(),
) -> list[PlanChangeOut]:
    """Ketua mengajukan adendum saat SK Berjalan (POST)."""
    return await controller.handle_request_amendment(access, plan_id, data)


@router.post("/amendments/{change_id}/reject", response_model=list[PlanChangeOut])
async def reject_amendment(
    plan_id: UUID,
    change_id: UUID,
    data: AmendmentReasonIn,
    access: PlanAccess = _PM_UNIT,
    controller: WorkPlanAmendmentsController = Depends(),
) -> list[PlanChangeOut]:
    """PM menolak usulan adendum SK yang diajukan oleh ketua (POST)."""
    return await controller.handle_reject_amendment(access, plan_id, change_id, data)


@router.put("/amendments/{change_id}", response_model=PlanDetailOut)
async def apply_amendment(
    plan_id: UUID,
    change_id: UUID,
    data: PlanDraftRequest,
    access: PlanAccess = _PM_UNIT,
    controller: WorkPlanAmendmentsController = Depends(),
) -> PlanDetailOut:
    """PM menerima usulan dengan mengubah isi SK (PUT)."""
    return await controller.handle_apply_amendment(access, change_id, data)


@router.post("/amendments/{change_id}/accept", response_model=list[PlanChangeOut])
async def accept_amendment(
    plan_id: UUID,
    change_id: UUID,
    access: PlanAccess = _LEADER,
    controller: WorkPlanAmendmentsController = Depends(),
) -> list[PlanChangeOut]:
    """Ketua menandatangani adendum (POST)."""
    return await controller.handle_accept_amendment(access, plan_id, change_id)


@router.get("/completion/html", response_class=HTMLResponse)
async def final_report_html(
    plan_id: UUID,
    access: PlanAccess = _VIEW,
    controller: WorkPlanAmendmentsController = Depends(),
) -> HTMLResponse:
    """Mendapatkan laporan akhir yang disetujui (A4, TTD ketua & PM + QR) (GET)."""
    return await controller.handle_final_report_html(access, plan_id)


__all__ = ["router"]
