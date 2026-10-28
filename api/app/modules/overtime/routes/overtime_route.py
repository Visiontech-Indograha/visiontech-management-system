"""
app/modules/overtime/routes/overtime_route.py

Rute endpoint HTTP untuk pengajuan lembur (/overtime).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import get_current_user, require_permission
from app.core.list_params import ListParams, apply_list
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
    response: Response,
    params: ListParams = Depends(),
    status: str | None = Query(None, max_length=30, description="Filter status lembur"),
    daily_plan_id: UUID | None = Query(None, description="ID jadwal harian"),
    work_plan_id: UUID | None = Query(None, description="Alias daily_plan_id"),
    current_user: CurrentUser = Depends(get_current_user),
    controller: OvertimeController = Depends(),
) -> list[OvertimeResponse]:
    """Daftar lembur untuk satu jadwal harian."""
    rows = await controller.handle_list(current_user, daily_plan_id or work_plan_id)
    return list(
        apply_list(
            rows,
            params,
            response,
            lambda r: (r.employee_name, r.reason),
            extra=lambda r: status is None or r.status == status,
        )
    )


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
