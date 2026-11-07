"""
app/modules/offices/routes/office_route.py

Rute endpoint HTTP master kantor pusat & cabang (/offices, tabel office).
Mengikuti Panduan Standar Arofficektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_current_user, require_permission, require_permission_for_office
from app.core.list_params import ListParams, apply_list
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.offices.controllers.office_controller import OfficeController
from app.modules.offices.schemas.office_schema import OfficeCreate, OfficeResponse, OfficeUpdate

router = APIRouter(prefix="/offices", tags=["Offices"])


@router.get("", response_model=list[OfficeResponse])
async def get_offices(
    response: Response,
    params: ListParams = Depends(),
    for_attendance: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    controller: OfficeController = Depends(),
) -> list[OfficeResponse]:
    """
    Daftar kantor aktif (GET). Terbuka untuk semua pengguna; `can_manage` menandai hak kelola.
    """
    rows = await controller.handle_list_offices(current_user, for_attendance)
    return list(apply_list(rows, params, response, lambda o: (o.name, o.address), prefix=True))

_MANAGE_TARGET = Depends(require_permission_for_office(Permission.MANAGE_SITES, "office_id"))


@router.post("", response_model=OfficeResponse, status_code=status.HTTP_201_CREATED)
async def create_office(
    data: OfficeCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_SITES)),
    controller: OfficeController = Depends(),
) -> OfficeResponse:
    """
    Membuat kantor baru (POST) — izin manage:offices.
    """
    return await controller.handle_create_office(current_user, data)


@router.put("/{office_id}", response_model=OfficeResponse)
async def update_office(
    office_id: UUID,
    data: OfficeUpdate,
    current_user: CurrentUser = _MANAGE_TARGET,
    controller: OfficeController = Depends(),
) -> OfficeResponse:
    """
    Mengubah data kantor (PUT, sebagian) — izin manage:offices.
    """
    return await controller.handle_update_office(current_user, office_id, data)


@router.delete("/{office_id}")
async def delete_office(
    office_id: UUID,
    current_user: CurrentUser = _MANAGE_TARGET,
    controller: OfficeController = Depends(),
) -> dict[str, str]:
    """
    Menghapus (arsip) kantor cabang (DELETE) — izin manage:offices.
    """
    return await controller.handle_delete_office(current_user, office_id)
