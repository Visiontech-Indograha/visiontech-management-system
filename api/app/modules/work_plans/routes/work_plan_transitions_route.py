"""
app/modules/work_plans/routes/work_plan_transitions_route.py

Rute endpoint HTTP untuk transisi status SK (/work-plans/{plan_id}).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.api.deps import plan_access
from app.modules.work_plans.controllers.work_plan_transitions_controller import (
    WorkPlanTransitionsController,
)
from app.modules.work_plans.schemas.work_plan_schema import (
    CompletionRequest,
    FinalReportOut,
    FinalReportSignatureOut,
    TransitionRequest,
    WorkPlanResponse,
)
from app.shared.access.access_service import PlanAccess, PlanNeed

router = APIRouter(prefix="/work-plans/{plan_id}", tags=["Work Plan Transitions"])
_LEADER_ACCESS = Depends(plan_access(PlanNeed.LEADER))
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))
_PM_UNIT_ANY_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT, archived=None))  # aktif maupun terarsip
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))


@router.get("/completion/signatures", response_model=list[FinalReportSignatureOut])
async def get_final_report_signatures(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    controller: WorkPlanTransitionsController = Depends(),
) -> list[FinalReportSignatureOut]:
    """Mengambil daftar tanda tangan laporan akhir (GET)."""
    return await controller.handle_get_signatures(plan_id)


@router.get("/completion/pdf", response_class=Response)
async def get_final_report_pdf(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    controller: WorkPlanTransitionsController = Depends(),
) -> Response:
    """Mengunduh PDF laporan akhir ber-QR (GET)."""
    return await controller.handle_get_pdf(access, plan_id)


@router.get("/completion", response_model=FinalReportOut | None)
async def get_final_report(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    controller: WorkPlanTransitionsController = Depends(),
) -> FinalReportOut | None:
    """Mengambil data laporan akhir SK (GET)."""
    return await controller.handle_get_final_report(plan_id)


@router.post("/publish", response_model=WorkPlanResponse)
async def publish_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    controller: WorkPlanTransitionsController = Depends(),
) -> WorkPlanResponse:
    """PM menerbitkan SK (POST)."""
    return await controller.handle_publish(access, plan_id, data)


@router.post("/accept", response_model=WorkPlanResponse)
async def accept_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    controller: WorkPlanTransitionsController = Depends(),
) -> WorkPlanResponse:
    """Ketua menerima SK yang diterbitkan PM (POST)."""
    return await controller.handle_accept(access, plan_id, data)


@router.post("/appeal", response_model=WorkPlanResponse)
async def appeal_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    controller: WorkPlanTransitionsController = Depends(),
) -> WorkPlanResponse:
    """Ketua mengajukan banding atas SK yang terbit (POST)."""
    return await controller.handle_appeal(access, plan_id, data)


@router.post("/revise", response_model=WorkPlanResponse)
async def revise_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    controller: WorkPlanTransitionsController = Depends(),
) -> WorkPlanResponse:
    """PM membuka revisi draf dari SK yang dibanding (POST)."""
    return await controller.handle_revise(access, plan_id, data)


@router.post("/cancel", response_model=WorkPlanResponse)
async def cancel_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    controller: WorkPlanTransitionsController = Depends(),
) -> WorkPlanResponse:
    """Membatalkan rencana kerja (POST)."""
    return await controller.handle_cancel(access, plan_id, data)


@router.post("/archive", response_model=WorkPlanResponse)
async def archive_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    controller: WorkPlanTransitionsController = Depends(),
) -> WorkPlanResponse:
    """Mengarsipkan (menghapus secara logis) draf SK (POST)."""
    return await controller.handle_archive(access, plan_id, data)


@router.post("/restore", response_model=WorkPlanResponse)
async def restore_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ANY_ACCESS,
    controller: WorkPlanTransitionsController = Depends(),
) -> WorkPlanResponse:
    """Memulihkan draf SK terarsip (POST)."""
    return await controller.handle_restore(access, plan_id, data)


@router.post("/start", response_model=WorkPlanResponse)
async def start_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    controller: WorkPlanTransitionsController = Depends(),
) -> WorkPlanResponse:
    """Ketua memulai pekerjaan berdasarkan SK yang telah diterima (POST)."""
    return await controller.handle_start(access, plan_id, data)


@router.post("/request-completion", response_model=WorkPlanResponse)
async def request_completion(
    plan_id: UUID,
    data: CompletionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    controller: WorkPlanTransitionsController = Depends(),
) -> WorkPlanResponse:
    """Ketua menyerahkan laporan akhir (POST)."""
    return await controller.handle_request_completion(access, plan_id, data)


@router.post("/approve-completion", response_model=WorkPlanResponse)
async def approve_completion(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    controller: WorkPlanTransitionsController = Depends(),
) -> WorkPlanResponse:
    """PM unit/OPS menutup SK setelah menyetujui laporan akhir (POST)."""
    return await controller.handle_approve_completion(access, plan_id, data)


@router.post("/return-completion", response_model=WorkPlanResponse)
async def return_completion(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    controller: WorkPlanTransitionsController = Depends(),
) -> WorkPlanResponse:
    """PM unit/OPS mengembalikan laporan akhir ke ketua (POST)."""
    return await controller.handle_return_completion(access, plan_id, data)


__all__ = ["router"]
