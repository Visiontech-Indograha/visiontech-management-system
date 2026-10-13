"""
app/modules/overtime/routes/overtime_route.py

Rute endpoint HTTP untuk pengajuan lembur (/overtime).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.overtime.controllers.overtime_controller import OvertimeController
from app.modules.overtime.schemas.overtime_schema import (
    OvertimeCreate,
    OvertimeResponse,
    OvertimeReview,
)

router = APIRouter(prefix="/overtime", tags=["Overtime"])


@router.post("", response_model=OvertimeResponse, status_code=status.HTTP_201_CREATED)
async def report_overtime(
    data: OvertimeCreate,
    current_user: CurrentUser = Depends(get_current_user),
    controller: OvertimeController = Depends(),
) -> OvertimeResponse:
    """Mengajukan permohonan lembur pada work plan yang aktif."""
    return await controller.handle_report(current_user, data)


@router.get("", response_model=list[OvertimeResponse])
async def list_overtime(
    work_plan_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: OvertimeController = Depends(),
) -> list[OvertimeResponse]:
    """Mendapatkan daftar lembur untuk satu work plan."""
    return await controller.handle_list_by_plan(current_user, work_plan_id)


@router.post("/{ot_id}/review", response_model=OvertimeResponse)
async def review_overtime(
    ot_id: UUID,
    data: OvertimeReview,
    current_user: CurrentUser = Depends(get_current_user),
    controller: OvertimeController = Depends(),
) -> OvertimeResponse:
    """Menyetujui atau menolak pengajuan lembur."""
    return await controller.handle_review(current_user, ot_id, data)
