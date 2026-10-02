"""
Transisi SK: terbitkan (PM unit/OPS), terima & mulai (ketua menurut SK) — dijaga `plan_access`
(V-07). Tipis (dok 12 §2): aturan di services/plan_transition_service.py, SQL di
crud/crud_plan_transition.py.
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user, get_plan_transition_service, get_signature_service, plan_access
from app.schemas.plan import WorkPlanResponse
from app.schemas.plan_transition import (
    CompletionRequest,
    FinalReportOut,
    FinalReportSignatureOut,
    TransitionRequest,
)
from app.services.access_service import PlanAccess, PlanNeed, ensure_same_org
from app.services.pdf_service import html_to_pdf, render_final_report_html
from app.services.plan_transition_service import PlanTransitionService
from app.services.signature_service import SignatureService

router = APIRouter(prefix="/work-plans/{plan_id}", tags=["Work Plan Transitions"])
_LEADER_ACCESS = Depends(plan_access(PlanNeed.LEADER))
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))
_PM_UNIT_ANY_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT, archived=None))  # aktif maupun terarsip
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))






@router.get("/completion/signatures", response_model=list[FinalReportSignatureOut])
async def get_final_report_signatures(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    signature_service: SignatureService = Depends(get_signature_service),
) -> list[FinalReportSignatureOut]:
    """Tanda tangan laporan akhir (ketua = ISSUER, pemeriksa = APPROVER), R-19."""
    rows = await signature_service.final_report_signatures(plan_id)
    return [FinalReportSignatureOut(**r._mapping) for r in rows]


@router.get("/completion/pdf", response_class=Response)
async def get_final_report_pdf(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    signature_service: SignatureService = Depends(get_signature_service),
) -> Response:
    """PDF laporan akhir ber-QR (P6-4, UAT langkah 10). Hanya setelah disetujui (409). Render → threadpool."""
    plan, signatures = await signature_service.final_report_with_qr(access.user, plan_id)
    pdf = await run_in_threadpool(html_to_pdf, render_final_report_html(plan, signatures))
    filename = f"{plan.number}-laporan-akhir.pdf".replace("/", "-")
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})


@router.get("/completion", response_model=FinalReportOut | None)
async def get_final_report(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> FinalReportOut | None:
    """Laporan akhir SK — dibaca PM sebelum menyetujui/mengembalikan, dan untuk mode presentasi.
    null bila belum pernah diajukan; SK tak terlihat → 404 (penjaga VIEW)."""
    row = await plan_transition_service.final_report(plan_id)
    return FinalReportOut(**row._mapping) if row else None




def _response(row: Any) -> WorkPlanResponse:
    return WorkPlanResponse(**row._mapping)


@router.post("/publish", response_model=WorkPlanResponse)
async def publish_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    plan = await plan_transition_service.publish(plan_id, access.user.organization_id, access.user.user_id, data.row_version)
    return _response(plan)


@router.post("/accept", response_model=WorkPlanResponse)
async def accept_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    plan = await plan_transition_service.accept(plan_id, access.user.organization_id, access.user.user_id, data.row_version)
    return _response(plan)


@router.post("/appeal", response_model=WorkPlanResponse)
async def appeal_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """domain.js APPEAL (V-20): ketua mengajukan banding atas SK terbit."""
    plan = await plan_transition_service.appeal(plan_id, access.user.organization_id, access.user.user_id,
                                     data.row_version, data.reason)
    return _response(plan)


@router.post("/revise", response_model=WorkPlanResponse)
async def revise_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """domain.js REVISE (V-20): PM membuka revisi draf dari SK yang dibanding."""
    plan = await plan_transition_service.revise(plan_id, access.user.organization_id, data.row_version)
    return _response(plan)


@router.post("/cancel", response_model=WorkPlanResponse)
async def cancel_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """domain.js CANCEL_PLAN (V-21)."""
    return _response(await plan_transition_service.cancel_plan(plan_id, access.user.organization_id,
                                                     data.row_version, data.reason))


@router.post("/archive", response_model=WorkPlanResponse)
async def archive_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """domain.js DELETE_PLAN (V-21): arsip draf — soft delete, riwayat tetap ada."""
    return _response(await plan_transition_service.delete_plan(plan_id, access.user.organization_id, access.user.user_id,
                                                    data.row_version, data.reason))


@router.post("/restore", response_model=WorkPlanResponse)
async def restore_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ANY_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """domain.js RESTORE_PLAN (V-21): pulihkan draf terarsip."""
    return _response(await plan_transition_service.restore_plan(plan_id, access.user.organization_id, data.row_version))


@router.post("/start", response_model=WorkPlanResponse)
async def start_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    plan = await plan_transition_service.start(plan_id, access.user.organization_id, access.user.user_id, data.row_version)
    return _response(plan)




@router.post("/request-completion", response_model=WorkPlanResponse)
async def request_completion(
    plan_id: UUID,
    data: CompletionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """domain.js REQUEST_COMPLETE (V-26): ketua menyerahkan laporan akhir → COMPLETION_REVIEW."""
    await ensure_same_org(db, access.user.organization_id, files=data.evidence_file_ids)
    return _response(await plan_transition_service.request_complete(
        plan_id, access.user.organization_id, access.user.user_id, data.row_version,
        data.body, data.obstacle, data.evidence_file_ids))


@router.post("/approve-completion", response_model=WorkPlanResponse)
async def approve_completion(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """domain.js APPROVE_COMPLETE (V-26): PM unit/OPS menutup SK → COMPLETED."""
    return _response(await plan_transition_service.approve_complete(
        plan_id, access.user.organization_id, access.user.user_id, data.row_version, data.reason))


@router.post("/return-completion", response_model=WorkPlanResponse)
async def return_completion(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """domain.js RETURN_COMPLETE (V-26): PM unit/OPS mengembalikan ke ketua → IN_PROGRESS."""
    return _response(await plan_transition_service.return_complete(
        plan_id, access.user.organization_id, access.user.user_id, data.row_version, data.reason))
