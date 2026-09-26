"""
Transisi SK: terbitkan (PM unit/OPS), terima & mulai (ketua menurut SK) — dijaga `plan_access`
(V-07). Tipis (dok 12 §2): aturan di services/plan_transition_service.py, SQL di
repositories/plan_transition_repo.py.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.api.guards import PlanAccess, PlanNeed, ensure_same_org, plan_access
from app.repositories.plan_member_repo import PlanMemberRepo
from app.repositories.plan_transition_repo import PlanTransitionRepo
from app.schemas.plan import WorkPlanResponse
from app.services.plan_transition_service import PlanTransitionService

router = APIRouter(prefix="/work-plans/{plan_id}", tags=["Work Plan Transitions"])
_LEADER_ACCESS = Depends(plan_access(PlanNeed.LEADER))
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))
_PM_UNIT_ANY_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT, archived=None))  # aktif maupun terarsip
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))


class FinalReportOut(BaseModel):
    status: str  # SUBMITTED | CHANGES_REQUESTED | APPROVED
    body: str
    obstacle: str | None
    evidence_file_ids: list[str]
    submitted_at: datetime | None
    submitted_by_name: str | None
    review_note: str | None
    reviewed_at: datetime | None
    reviewed_by_name: str | None


@router.get("/completion", response_model=FinalReportOut | None)
async def get_final_report(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> FinalReportOut | None:
    """Laporan akhir SK — dibaca PM sebelum menyetujui/mengembalikan, dan untuk mode presentasi.
    null bila belum pernah diajukan; SK tak terlihat → 404 (penjaga VIEW)."""
    row = await _service(db).final_report(plan_id)
    return FinalReportOut(**row._mapping) if row else None


class TransitionRequest(BaseModel):
    row_version: int
    reason: str = ""


def _service(db: AsyncSession) -> PlanTransitionService:
    return PlanTransitionService(PlanTransitionRepo(db), PlanMemberRepo(db))


def _response(row: Any) -> WorkPlanResponse:
    return WorkPlanResponse(**row._mapping)


@router.post("/publish", response_model=WorkPlanResponse)
async def publish_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    plan = await _service(db).publish(plan_id, access.user.organization_id, access.user.user_id, data.row_version)
    return _response(plan)


@router.post("/accept", response_model=WorkPlanResponse)
async def accept_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    plan = await _service(db).accept(plan_id, access.user.organization_id, access.user.user_id, data.row_version)
    return _response(plan)


@router.post("/appeal", response_model=WorkPlanResponse)
async def appeal_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    """domain.js APPEAL (V-20): ketua mengajukan banding atas SK terbit."""
    plan = await _service(db).appeal(plan_id, access.user.organization_id, access.user.user_id,
                                     data.row_version, data.reason)
    return _response(plan)


@router.post("/revise", response_model=WorkPlanResponse)
async def revise_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    """domain.js REVISE (V-20): PM membuka revisi draf dari SK yang dibanding."""
    plan = await _service(db).revise(plan_id, access.user.organization_id, data.row_version)
    return _response(plan)


@router.post("/cancel", response_model=WorkPlanResponse)
async def cancel_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    """domain.js CANCEL_PLAN (V-21)."""
    return _response(await _service(db).cancel_plan(plan_id, access.user.organization_id,
                                                     data.row_version, data.reason))


@router.post("/archive", response_model=WorkPlanResponse)
async def archive_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    """domain.js DELETE_PLAN (V-21): arsip draf — soft delete, riwayat tetap ada."""
    return _response(await _service(db).delete_plan(plan_id, access.user.organization_id, access.user.user_id,
                                                    data.row_version, data.reason))


@router.post("/restore", response_model=WorkPlanResponse)
async def restore_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ANY_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    """domain.js RESTORE_PLAN (V-21): pulihkan draf terarsip."""
    return _response(await _service(db).restore_plan(plan_id, access.user.organization_id, data.row_version))


@router.post("/start", response_model=WorkPlanResponse)
async def start_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    plan = await _service(db).start(plan_id, access.user.organization_id, access.user.user_id, data.row_version)
    return _response(plan)


class CompletionRequest(BaseModel):
    row_version: int
    body: str
    obstacle: str
    evidence_file_ids: list[UUID] = []


@router.post("/request-completion", response_model=WorkPlanResponse)
async def request_completion(
    plan_id: UUID,
    data: CompletionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    """domain.js REQUEST_COMPLETE (V-26): ketua menyerahkan laporan akhir → COMPLETION_REVIEW."""
    await ensure_same_org(db, access.user.organization_id, files=data.evidence_file_ids)
    return _response(await _service(db).request_complete(
        plan_id, access.user.organization_id, access.user.user_id, data.row_version,
        data.body, data.obstacle, data.evidence_file_ids))


@router.post("/approve-completion", response_model=WorkPlanResponse)
async def approve_completion(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    """domain.js APPROVE_COMPLETE (V-26): PM unit/OPS menutup SK → COMPLETED."""
    return _response(await _service(db).approve_complete(
        plan_id, access.user.organization_id, access.user.user_id, data.row_version, data.reason))


@router.post("/return-completion", response_model=WorkPlanResponse)
async def return_completion(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    """domain.js RETURN_COMPLETE (V-26): PM unit/OPS mengembalikan ke ketua → IN_PROGRESS."""
    return _response(await _service(db).return_complete(
        plan_id, access.user.organization_id, access.user.user_id, data.row_version, data.reason))
