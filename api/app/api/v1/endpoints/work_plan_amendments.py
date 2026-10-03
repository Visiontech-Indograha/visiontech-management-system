"""
Adendum saat SK Berjalan (alur SK v2 PR3, flowchart SK2-E) & dokumen laporan akhir.
Tipis (dok 12 §2): aturan di services/plan_amendment_service.py.
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.api.deps import get_plan_amendment_service, get_signature_service, plan_access
from app.schemas.plan_draft import AmendmentReasonIn, PlanChangeOut, PlanDetailOut, PlanDraftRequest
from app.services.access_service import PlanAccess, PlanNeed
from app.services.pdf_service import render_final_report_html
from app.services.plan_amendment_service import PlanAmendmentService
from app.services.signature_service import SignatureService

router = APIRouter(prefix="/work-plans/{plan_id}", tags=["Work Plan Amendments"])
_VIEW = Depends(plan_access(PlanNeed.VIEW))
_LEADER = Depends(plan_access(PlanNeed.LEADER))
_PM_UNIT = Depends(plan_access(PlanNeed.PM_UNIT))


@router.get("/changes", response_model=list[PlanChangeOut])
async def list_changes(plan_id: UUID, access: PlanAccess = _VIEW,
                       plan_amendment_service: PlanAmendmentService = Depends(get_plan_amendment_service),
                       ) -> list[PlanChangeOut]:
    """Riwayat usulan perubahan SK (menutup celah: usulan tidak bisa dibaca ulang, docs/28)."""
    return [PlanChangeOut(**r._mapping) for r in await plan_amendment_service.list_changes(plan_id)]


@router.post("/amendments", response_model=list[PlanChangeOut])
async def request_amendment(plan_id: UUID, data: AmendmentReasonIn, access: PlanAccess = _LEADER,
                            plan_amendment_service: PlanAmendmentService = Depends(get_plan_amendment_service),
                            ) -> list[PlanChangeOut]:
    """Ketua mengajukan adendum saat SK Berjalan (status SK tetap Berjalan)."""
    await plan_amendment_service.request_amendment(access, data.reason)
    return [PlanChangeOut(**r._mapping) for r in await plan_amendment_service.list_changes(plan_id)]


@router.post("/amendments/{change_id}/reject", response_model=list[PlanChangeOut])
async def reject_amendment(plan_id: UUID, change_id: UUID, data: AmendmentReasonIn, access: PlanAccess = _PM_UNIT,
                           plan_amendment_service: PlanAmendmentService = Depends(get_plan_amendment_service),
                           ) -> list[PlanChangeOut]:
    await plan_amendment_service.reject_amendment(access, change_id, data.reason)
    return [PlanChangeOut(**r._mapping) for r in await plan_amendment_service.list_changes(plan_id)]


@router.put("/amendments/{change_id}", response_model=PlanDetailOut)
async def apply_amendment(plan_id: UUID, change_id: UUID, data: PlanDraftRequest, access: PlanAccess = _PM_UNIT,
                          plan_amendment_service: PlanAmendmentService = Depends(get_plan_amendment_service),
                          ) -> PlanDetailOut:
    """PM menerima usulan dengan mengubah isi SK; dokumen adendum terbit dengan tanda tangan PM."""
    return PlanDetailOut(**await plan_amendment_service.apply_amendment(access, change_id, data))


@router.post("/amendments/{change_id}/accept", response_model=list[PlanChangeOut])
async def accept_amendment(plan_id: UUID, change_id: UUID, access: PlanAccess = _LEADER,
                           plan_amendment_service: PlanAmendmentService = Depends(get_plan_amendment_service),
                           ) -> list[PlanChangeOut]:
    """Ketua menandatangani adendum; versi SK lama Tidak berlaku."""
    await plan_amendment_service.accept_amendment(access, change_id)
    return [PlanChangeOut(**r._mapping) for r in await plan_amendment_service.list_changes(plan_id)]


@router.get("/completion/html", response_class=HTMLResponse)
async def final_report_html(plan_id: UUID, access: PlanAccess = _VIEW,
                            signature_service: SignatureService = Depends(get_signature_service)) -> HTMLResponse:
    """Laporan akhir yang disetujui (A4, TTD ketua & PM + QR) — penampil web & HP."""
    plan, signatures = await signature_service.final_report_with_qr(access.user, plan_id)
    return HTMLResponse(render_final_report_html(plan, signatures))
