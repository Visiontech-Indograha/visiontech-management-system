"""
app/modules/employees/routes/employee_route.py
Rute karyawan V2 (Milestone 10): direktori, data kerja (kantor/divisi/jabatan/PKWT), alamat, arsip.
Akun login: modul accounts; dokumen: modul documents; akhir masa kerja: modul offboarding.
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.employees.controllers.employee_controller import EmployeeController
from app.modules.employees.schemas.employee_schema import (
    AddressIn,
    AddressOut,
    EmployeeCreate,
    EmployeeDetail,
    EmployeeListResponse,
    EmployeeOut,
    EmployeeUpdate,
)

router = APIRouter(prefix="/employees", tags=["Employees"])
_VIEW = Depends(require_permission(Permission.VIEW_USERS))
_MANAGE = Depends(require_permission(Permission.MANAGE_USERS))
_DELETE_ANY = Depends(require_permission(Permission.DELETE_ANY))


def _sees_private(user: CurrentUser, employee_id: UUID) -> bool:
    """Kontak pribadi (telepon, email, alamat) hanya untuk pemiliknya dan pengelola karyawan (HR/admin)."""
    return Permission.MANAGE_USERS.value in user.permissions or str(employee_id) == (user.employee_id or "")


def _private_hidden[T: EmployeeOut](emp: T, user: CurrentUser) -> T:
    if _sees_private(user, emp.employee_id):
        return emp
    hidden: dict[str, object] = {"phone_number": None, "email": None, "city": None}
    if isinstance(emp, EmployeeDetail):
        hidden["addresses"] = []
    return emp.model_copy(update=hidden)


@router.get("", response_model=EmployeeListResponse)
async def list_employees(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    employee_status: Literal["active", "in_process", "offboarded", "archived", "all"] | None = Query(
        None, alias="status", description="Kosong = semua yang belum diarsipkan"),
    division_id: UUID | None = None,
    office_id: UUID | None = None,
    position_id: UUID | None = None,
    q: str | None = None,
    current_user: CurrentUser = _VIEW,
    controller: EmployeeController = Depends(),
) -> EmployeeListResponse:
    """Direktori karyawan (cari nama / no. karyawan / email; saring status, divisi, kantor, jabatan)."""
    result = await controller.list(page=page, size=size, status=employee_status, division_id=division_id,
                                   office_id=office_id, position_id=position_id, q=q)
    return result.model_copy(update={"items": [_private_hidden(e, current_user) for e in result.items]})


@router.get("/{employee_id}", response_model=EmployeeDetail)
async def get_employee(
    employee_id: UUID,
    current_user: CurrentUser = _VIEW,
    controller: EmployeeController = Depends(),
) -> EmployeeDetail:
    """Detail karyawan + alamat (kontak pribadi hanya untuk pemilik & HR/admin)."""
    return _private_hidden(await controller.detail(employee_id), current_user)


@router.post("", response_model=EmployeeDetail, status_code=status.HTTP_201_CREATED)
async def create_employee(
    data: EmployeeCreate,
    current_user: CurrentUser = _MANAGE,
    controller: EmployeeController = Depends(),
) -> EmployeeDetail:
    """Karyawan baru (akun login dibuat terpisah lewat /employees/{id}/account)."""
    return await controller.create(data)


@router.put("/{employee_id}", response_model=EmployeeDetail)
async def update_employee(
    employee_id: UUID,
    data: EmployeeUpdate,
    current_user: CurrentUser = _MANAGE,
    controller: EmployeeController = Depends(),
) -> EmployeeDetail:
    """Ubah data karyawan (sebagian)."""
    return await controller.update(employee_id, data)


@router.post("/{employee_id}/addresses", response_model=AddressOut, status_code=status.HTTP_201_CREATED)
async def add_address(
    employee_id: UUID,
    data: AddressIn,
    current_user: CurrentUser = _MANAGE,
    controller: EmployeeController = Depends(),
) -> AddressOut:
    """Tambah alamat karyawan."""
    return await controller.add_address(employee_id, data)


@router.put("/{employee_id}/addresses/{address_id}", response_model=AddressOut)
async def update_address(
    employee_id: UUID,
    address_id: UUID,
    data: AddressIn,
    current_user: CurrentUser = _MANAGE,
    controller: EmployeeController = Depends(),
) -> AddressOut:
    """Ubah alamat karyawan."""
    return await controller.update_address(employee_id, address_id, data)


@router.delete("/{employee_id}/addresses/{address_id}")
async def delete_address(
    employee_id: UUID,
    address_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: EmployeeController = Depends(),
) -> dict[str, str]:
    """Hapus alamat karyawan."""
    return await controller.delete_address(employee_id, address_id)


@router.post("/{employee_id}/archive")
async def archive_employee(
    employee_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: EmployeeController = Depends(),
) -> dict[str, str]:
    """Arsipkan karyawan yang sudah selesai offboarding."""
    return await controller.archive(employee_id)


@router.delete("/{employee_id}")
async def delete_employee(
    employee_id: UUID,
    current_user: CurrentUser = _DELETE_ANY,
    controller: EmployeeController = Depends(),
) -> dict[str, str]:
    """Hapus permanen karyawan beserta akun loginnya — hanya SUPER_ADMIN, dan hanya yang sudah diarsipkan."""
    return await controller.delete(employee_id, current_user)


@router.post("/{employee_id}/restore")
async def restore_employee(
    employee_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: EmployeeController = Depends(),
) -> dict[str, str]:
    """Batalkan arsip (status tetap selesai bekerja)."""
    return await controller.restore(employee_id)
