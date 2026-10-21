"""
app/modules/divisions/routes/division_route.py

Rute endpoint HTTP divisi operasional (/divisions, tabel division).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.divisions.controllers.division_controller import DivisionController
from app.modules.divisions.schemas.division_schema import DivisionCreate, DivisionOut, DivisionUpdate

router = APIRouter(prefix="/divisions", tags=["Divisions"])
_MANAGE = Depends(require_permission(Permission.MANAGE_DIVISIONS))


@router.get("", response_model=list[DivisionOut])
async def list_divisions(
    current_user: CurrentUser = Depends(get_current_user),
    controller: DivisionController = Depends(),
) -> list[DivisionOut]:
    """Daftar divisi aktif beserta OM, PM, dan jumlah timnya (GET)."""
    return await controller.handle_list_divisions(current_user.organization_id)


@router.post("", response_model=DivisionOut, status_code=status.HTTP_201_CREATED)
async def create_division(
    data: DivisionCreate,
    current_user: CurrentUser = _MANAGE,
    controller: DivisionController = Depends(),
) -> DivisionOut:
    """Membuat divisi baru dengan OM & PM-nya (POST) — izin manage:divisions."""
    return await controller.handle_create_division(data)


@router.put("/{division_id}", response_model=DivisionOut)
async def update_division(
    division_id: UUID,
    data: DivisionUpdate,
    current_user: CurrentUser = _MANAGE,
    controller: DivisionController = Depends(),
) -> DivisionOut:
    """Mengubah divisi (PUT, sebagian) — izin manage:divisions."""
    return await controller.handle_update_division(division_id, data)


@router.delete("/{division_id}")
async def delete_division(
    division_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: DivisionController = Depends(),
) -> dict[str, str]:
    """Menghapus (arsip) divisi yang tidak lagi dipakai (DELETE) — izin manage:divisions."""
    return await controller.handle_delete_division(division_id)
