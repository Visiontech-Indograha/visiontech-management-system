"""
app/modules/mess/routes/mess_route.py
Rute API HTTP untuk entitas hunian mess karyawan (company_mess_stay).
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.mess.controllers.mess_controller import MessController
from app.modules.mess.schemas.mess_schema import (
    MessStayCreate,
    MessStayOut,
    MessStayUpdate,
)

router = APIRouter(prefix="/mess", tags=["Mess"])
_VIEW = Depends(require_permission(Permission.VIEW_MESS))
_MANAGE = Depends(require_permission(Permission.MANAGE_MESS))


@router.get("", response_model=list[MessStayOut])
async def list_stays(
    employee_id: UUID | None = Query(None, description="Filter berdasarkan ID karyawan"),
    start: date | None = Query(None, description="Hunian yang beririsan sejak tanggal ini"),
    end: date | None = Query(None, description="Hunian yang beririsan sampai tanggal ini"),
    current_user: CurrentUser = _VIEW,
    controller: MessController = Depends(),
) -> list[MessStayOut]:
    """Mengambil daftar riwayat dan jadwal hunian mess karyawan."""
    return await controller.handle_list_stays(current_user, employee_id, start, end)


@router.get("/me", response_model=list[MessStayOut])
async def my_stays(
    current_user: CurrentUser = Depends(get_current_user),
    controller: MessController = Depends(),
) -> list[MessStayOut]:
    """Riwayat dan jadwal hunian mess milik sendiri (tanpa izin view:mess; hanya data akun ini)."""
    return await controller.handle_my_stays(current_user)


@router.get("/{mess_stay_id}", response_model=MessStayOut)
async def get_stay(
    mess_stay_id: UUID,
    current_user: CurrentUser = _VIEW,
    controller: MessController = Depends(),
) -> MessStayOut:
    """Mengambil detail hunian mess karyawan."""
    return await controller.handle_get_stay(current_user, mess_stay_id)


@router.post("", response_model=MessStayOut, status_code=201)
async def create_stay(
    data: MessStayCreate,
    current_user: CurrentUser = _MANAGE,
    controller: MessController = Depends(),
) -> MessStayOut:
    """Mencatat hunian mess karyawan baru."""
    return await controller.handle_create_stay(current_user, data)


@router.put("/{mess_stay_id}", response_model=MessStayOut)
async def update_stay(
    mess_stay_id: UUID,
    data: MessStayUpdate,
    current_user: CurrentUser = _MANAGE,
    controller: MessController = Depends(),
) -> MessStayOut:
    """Memperbarui informasi hunian mess karyawan."""
    return await controller.handle_update_stay(current_user, mess_stay_id, data)


@router.delete("/{mess_stay_id}")
async def delete_stay(
    mess_stay_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: MessController = Depends(),
) -> dict[str, str]:
    """Menghapus data hunian mess karyawan."""
    return await controller.handle_delete_stay(current_user, mess_stay_id)
