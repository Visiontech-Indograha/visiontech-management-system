"""
app/modules/units/routes/unit_route.py

Rute endpoint HTTP divisi operasional (/units, tabel division).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.units.controllers.unit_controller import UnitController
from app.modules.units.schemas.unit_schema import UnitCreate, UnitOut, UnitUpdate

router = APIRouter(prefix="/units", tags=["Units"])
_MANAGE = Depends(require_permission(Permission.MANAGE_DIVISIONS))


@router.get("", response_model=list[UnitOut])
async def list_units(
    current_user: CurrentUser = Depends(get_current_user),
    controller: UnitController = Depends(),
) -> list[UnitOut]:
    """Daftar divisi aktif beserta OM, PM, dan jumlah timnya (GET)."""
    return await controller.handle_list_units(current_user.organization_id)


@router.post("", response_model=UnitOut, status_code=status.HTTP_201_CREATED)
async def create_unit(
    data: UnitCreate,
    current_user: CurrentUser = _MANAGE,
    controller: UnitController = Depends(),
) -> UnitOut:
    """Membuat divisi baru dengan OM & PM-nya (POST) — izin manage:divisions."""
    return await controller.handle_create_unit(data)


@router.put("/{unit_id}", response_model=UnitOut)
async def update_unit(
    unit_id: UUID,
    data: UnitUpdate,
    current_user: CurrentUser = _MANAGE,
    controller: UnitController = Depends(),
) -> UnitOut:
    """Mengubah divisi (PUT, sebagian) — izin manage:divisions."""
    return await controller.handle_update_unit(unit_id, data)


@router.delete("/{unit_id}")
async def delete_unit(
    unit_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: UnitController = Depends(),
) -> dict[str, str]:
    """Menghapus (arsip) divisi yang tidak lagi dipakai (DELETE) — izin manage:divisions."""
    return await controller.handle_delete_unit(unit_id)
