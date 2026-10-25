"""
app/modules/overtime/routes/overtime_route.py

Rute endpoint HTTP untuk pengajuan lembur (/overtime).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
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
    """Mengajukan lembur atas jadwal harian yang sedang berjalan (ketua/anggota tim)."""
    return await controller.handle_report(current_user, data)


@router.get("", response_model=list[OvertimeResponse])
async def list_overtime(
    daily_plan_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: OvertimeController = Depends(),
) -> list[OvertimeResponse]:
    """Daftar lembur untuk satu jadwal harian."""
    return await controller.handle_list_by_plan(current_user, daily_plan_id)


@router.post("/{ot_id}/review", response_model=OvertimeResponse)
async def review_overtime(
    ot_id: UUID,
    data: OvertimeReview,
    current_user: CurrentUser = Depends(get_current_user),
    controller: OvertimeController = Depends(),
) -> OvertimeResponse:
    """Menyetujui atau menolak pengajuan lembur."""
    return await controller.handle_review(current_user, ot_id, data)


@router.delete("/{ot_id}")
async def delete_overtime(
    ot_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.DELETE_ANY)),
    controller: OvertimeController = Depends(),
) -> dict[str, str]:
    """Hapus permanen pengajuan lembur — hanya SUPER_ADMIN."""
    return await controller.handle_delete(current_user, ot_id)
