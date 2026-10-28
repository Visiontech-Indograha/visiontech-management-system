"""
app/modules/work_plans/routes/daily_correction_route.py
Rute koreksi laporan harian (/work-plans): ketua tim mengajukan → PM setujui/tolak → ketua revisi & kirim →
PM terima/kembalikan sampai diterima. Kewenangan diperiksa di DailyCorrectionService (akses jadwal harian).
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.work_plans.controllers.daily_correction_controller import DailyCorrectionController
from app.modules.work_plans.schemas.daily_correction_schema import CorrectionCreate, CorrectionDecide, CorrectionOut

router = APIRouter(prefix="/work-plans", tags=["Work Plans (Daily-First)"])
_LOGIN = Depends(get_current_user)


@router.get("/corrections", response_model=list[CorrectionOut])
async def correction_inbox(
    status_filter: str | None = Query(
        None, alias="status", pattern="^(REQUESTED|REVISING|IN_REVIEW|ACCEPTED|REJECTED)$"
    ),
    current_user: CurrentUser = _LOGIN,
    controller: DailyCorrectionController = Depends(),
) -> list[CorrectionOut]:
    """Daftar koreksi laporan: PM/OM divisinya, ketua tim yang diajukannya, admin semua."""
    return await controller.handle_inbox(current_user, status_filter)


@router.get("/daily/{daily_plan_id}/corrections", response_model=list[CorrectionOut])
async def plan_corrections(
    daily_plan_id: UUID, current_user: CurrentUser = _LOGIN, controller: DailyCorrectionController = Depends()
) -> list[CorrectionOut]:
    """Riwayat koreksi laporan satu jadwal harian."""
    return await controller.handle_of_plan(current_user, daily_plan_id)


@router.post("/daily/{daily_plan_id}/corrections", response_model=CorrectionOut, status_code=status.HTTP_201_CREATED)
async def request_correction(
    daily_plan_id: UUID, data: CorrectionCreate, current_user: CurrentUser = _LOGIN,
    controller: DailyCorrectionController = Depends(),
) -> CorrectionOut:
    """Ketua tim meminta koreksi laporan jadwal yang sudah COMPLETED."""
    return await controller.handle_request(current_user, daily_plan_id, data)


@router.post("/corrections/{correction_id}/decision", response_model=CorrectionOut)
async def decide_correction(
    correction_id: UUID, data: CorrectionDecide, current_user: CurrentUser = _LOGIN,
    controller: DailyCorrectionController = Depends(),
) -> CorrectionOut:
    """PM/OM divisi: setujui/tolak permintaan, atau terima/kembalikan hasil revisi."""
    return await controller.handle_decide(current_user, correction_id, data)


@router.post("/corrections/{correction_id}/submit", response_model=CorrectionOut)
async def submit_revision(
    correction_id: UUID, current_user: CurrentUser = _LOGIN, controller: DailyCorrectionController = Depends()
) -> CorrectionOut:
    """Ketua tim mengirim revisi untuk diperiksa PM."""
    return await controller.handle_submit(current_user, correction_id)
