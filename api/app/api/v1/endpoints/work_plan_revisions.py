"""
Revisi rencana kerja oleh PM kapan saja + riwayatnya (Rencana Kerja v3, T6).
Tipis (dok 12 §2): aturan di services/plan_revision_service.py. `POST /revise` lama tetap ada untuk APK lama.
"""
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_plan_revision_service, plan_access
from app.schemas.plan_draft import PlanDetailOut
from app.schemas.plan_revision import PlanRevisionIn, PlanRevisionOut
from app.services.access_service import PlanAccess, PlanNeed
from app.services.plan_revision_service import PlanRevisionService

router = APIRouter(prefix="/work-plans/{plan_id}", tags=["Work Plan Revisions"])
_VIEW = Depends(plan_access(PlanNeed.VIEW))
_PM_UNIT = Depends(plan_access(PlanNeed.PM_UNIT))


@router.post("/revisions", response_model=PlanDetailOut)
async def revise_plan(plan_id: UUID, data: PlanRevisionIn, access: PlanAccess = _PM_UNIT,
                      service: PlanRevisionService = Depends(get_plan_revision_service)) -> PlanDetailOut:
    """
    PM unit/OPS merevisi rencana kerja berstatus Terbit, Revisi diminta, Diterima, atau Berjalan (POST).
    Versi dokumen baru ditandatangani PM; ketua dan anggota mendapat notifikasi beserta diff.

    Path Parameters:
    - plan_id (UUID): ID rencana kerja.

    Request Body:
    - data (PlanRevisionIn): isi rencana kerja yang baru + `reason` + `change_id` (permintaan ketua, opsional).

    Returns:
    - PlanDetailOut: detail rencana kerja pasca revisi.
    """
    return PlanDetailOut(**await service.revise_plan(access, data))


@router.get("/revisions", response_model=list[PlanRevisionOut])
async def list_revisions(plan_id: UUID, access: PlanAccess = _VIEW,
                         service: PlanRevisionService = Depends(get_plan_revision_service)) -> list[PlanRevisionOut]:
    """
    Riwayat revisi rencana kerja, terbaru dulu (GET); siapa pun yang berhak melihat rencana kerja.

    Path Parameters:
    - plan_id (UUID): ID rencana kerja.

    Returns:
    - list[PlanRevisionOut]: revisi beserta diff sebelum/sesudah.
    """
    return [PlanRevisionOut(**r._mapping) for r in await service.list_revisions(plan_id)]
