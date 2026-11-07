"""
app/modules/employees/routes/employee_route.py
Rute karyawan V2 (Milestone 10): direktori, data kerja (kantor/divisi/jabatan/PKWT), alamat, arsip.
Akun login: modul accounts; dokumen: modul documents; akhir masa kerja: modul offboarding.
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, require_permission, require_permission_for_employee
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.employees.controllers.employee_controller import EmployeeController
from app.modules.employees.schemas.employee_schema import (
    AddressIn,
    AddressOut,
    EmployeeCreate,
    EmployeeDetail,
    EmployeeListResponse,
    EmployeeUpdate,
    MyPhotoIn,
    MyPhotoOut,
    NextEmployeeNo,
)

router = APIRouter(prefix="/employees", tags=["Employees"])
_VIEW = Depends(require_permission(Permission.VIEW_USERS))
_MANAGE = Depends(require_permission(Permission.MANAGE_USERS))
_MANAGE_TARGET = Depends(require_permission_for_employee(Permission.MANAGE_USERS, "employee_id"))
_DELETE_ANY = Depends(require_permission(Permission.DELETE_ANY))


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
    # Cakupan: karyawan/TL = dirinya, divisi, dan tim; PM = jangkauannya; HR/OM/SA/Finance/HSE/aset = semua.
    # Kolom sensitif (kontak, PKWT, peran sistem) hanya untuk HR/OM/SA, PM terkait, dan pemiliknya.
    return await controller.list(user=current_user, page=page, size=size, status=employee_status,
                                 division_id=division_id, office_id=office_id, position_id=position_id, q=q)


@router.get("/next-no", response_model=NextEmployeeNo, summary="Usulan nomor karyawan berikutnya")
async def next_employee_no(
    current_user: CurrentUser = _MANAGE,
    controller: EmployeeController = Depends(),
) -> NextEmployeeNo:
    """Awalan dan lebar angka mengikuti karyawan terbaru; pengguna tetap boleh mengubahnya."""
    return await controller.next_no()


@router.get("/{employee_id}", response_model=EmployeeDetail)
async def get_employee(
    employee_id: UUID,
    current_user: CurrentUser = _VIEW,
    controller: EmployeeController = Depends(),
) -> EmployeeDetail:
    """Detail karyawan + alamat (kontak pribadi hanya untuk pemilik & HR/admin)."""
    # Di luar cakupan → 404. Kontak & alamat hanya untuk pemilik, HR/OM/SA, dan PM terkait.
    return await controller.detail(current_user, employee_id)


@router.post("", response_model=EmployeeDetail, status_code=status.HTTP_201_CREATED)
async def create_employee(
    data: EmployeeCreate,
    current_user: CurrentUser = _MANAGE,
    controller: EmployeeController = Depends(),
) -> EmployeeDetail:
    """Karyawan baru (akun login dibuat terpisah lewat /employees/{id}/account)."""
    return await controller.create(data, current_user)


@router.put("/me/photo", response_model=MyPhotoOut)
async def set_my_photo(
    data: MyPhotoIn,
    current_user: CurrentUser = Depends(get_current_user),
    controller: EmployeeController = Depends(),
) -> MyPhotoOut:
    """Ganti (atau hapus, `file_id: null`) foto profil sendiri; berkas harus gambar unggahan pengguna ini."""
    return await controller.set_my_photo(current_user, data)


@router.put("/{employee_id}", response_model=EmployeeDetail)
async def update_employee(
    employee_id: UUID,
    data: EmployeeUpdate,
    current_user: CurrentUser = _MANAGE_TARGET,
    controller: EmployeeController = Depends(),
) -> EmployeeDetail:
    """Ubah data karyawan (sebagian)."""
    return await controller.update(employee_id, data, current_user)


@router.post("/{employee_id}/addresses", response_model=AddressOut, status_code=status.HTTP_201_CREATED)
async def add_address(
    employee_id: UUID,
    data: AddressIn,
    current_user: CurrentUser = _MANAGE_TARGET,
    controller: EmployeeController = Depends(),
) -> AddressOut:
    """Tambah alamat karyawan."""
    return await controller.add_address(employee_id, data)


@router.put("/{employee_id}/addresses/{address_id}", response_model=AddressOut)
async def update_address(
    employee_id: UUID,
    address_id: UUID,
    data: AddressIn,
    current_user: CurrentUser = _MANAGE_TARGET,
    controller: EmployeeController = Depends(),
) -> AddressOut:
    """Ubah alamat karyawan."""
    return await controller.update_address(employee_id, address_id, data)


@router.delete("/{employee_id}/addresses/{address_id}")
async def delete_address(
    employee_id: UUID,
    address_id: UUID,
    current_user: CurrentUser = _MANAGE_TARGET,
    controller: EmployeeController = Depends(),
) -> dict[str, str]:
    """Hapus alamat karyawan."""
    return await controller.delete_address(employee_id, address_id)


@router.post("/{employee_id}/archive")
async def archive_employee(
    employee_id: UUID,
    current_user: CurrentUser = _MANAGE_TARGET,
    controller: EmployeeController = Depends(),
) -> dict[str, str]:
    """Arsipkan karyawan yang sudah selesai offboarding."""
    return await controller.archive(employee_id, current_user)


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
    current_user: CurrentUser = _MANAGE_TARGET,
    controller: EmployeeController = Depends(),
) -> dict[str, str]:
    """Batalkan arsip (status tetap selesai bekerja)."""
    return await controller.restore(employee_id, current_user)
