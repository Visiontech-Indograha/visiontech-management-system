"""
app/modules/employees/routes/employee_route.py

Rute endpoint HTTP untuk data karyawan (/employees).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.employees.controllers.employee_controller import EmployeeController
from app.modules.employees.schemas.employee_schema import (
    EmergencyContactCreate,
    EmergencyContactResponse,
    EmergencyContactUpdate,
    EmployeeAssignmentCreate,
    EmployeeAssignmentResponse,
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeOffboard,
    EmployeeResponse,
    EmployeeUpdate,
)

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get("", response_model=EmployeeListResponse)
async def get_employees(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    is_active: bool | None = None,
    q: str | None = None,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_USERS)),
    controller: EmployeeController = Depends(),
) -> EmployeeListResponse:
    """Mendapatkan daftar karyawan di organisasi pengguna dengan paginasi dan pencarian."""
    return await controller.handle_list_employees(current_user, page, size, is_active, q)


@router.get("/{emp_id}", response_model=EmployeeResponse)
async def get_employee(
    emp_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_USERS)),
    controller: EmployeeController = Depends(),
) -> EmployeeResponse:
    """Detail satu karyawan berdasarkan ID."""
    return await controller.handle_get_employee(current_user, emp_id)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    data: EmployeeCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    controller: EmployeeController = Depends(),
) -> EmployeeResponse:
    """Menambahkan data karyawan baru ke dalam organisasi."""
    return await controller.handle_create_employee(current_user, data)


@router.put("/{emp_id}", response_model=EmployeeResponse)
async def update_employee(
    emp_id: UUID,
    data: EmployeeUpdate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    controller: EmployeeController = Depends(),
) -> EmployeeResponse:
    """Mengubah data pribadi karyawan."""
    return await controller.handle_update_employee(current_user, emp_id, data)


@router.get("/{emp_id}/assignments", response_model=list[EmployeeAssignmentResponse])
async def list_assignments(
    emp_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_USERS)),
    controller: EmployeeController = Depends(),
) -> list[EmployeeAssignmentResponse]:
    """Riwayat jabatan/penempatan karyawan."""
    return await controller.handle_list_assignments(current_user, emp_id)


@router.post("/{emp_id}/assignments", response_model=EmployeeAssignmentResponse)
async def add_assignment(
    emp_id: UUID,
    data: EmployeeAssignmentCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    controller: EmployeeController = Depends(),
) -> EmployeeAssignmentResponse:
    """Mutasi atau promosi jabatan baru bagi karyawan."""
    return await controller.handle_add_assignment(current_user, emp_id, data)


@router.post("/{emp_id}/offboard")
async def offboard_employee(
    emp_id: UUID,
    data: EmployeeOffboard,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    controller: EmployeeController = Depends(),
) -> dict[str, Any]:
    """HR mengakhiri masa kerja karyawan."""
    return await controller.handle_offboard(current_user, emp_id, data)


@router.post("/{emp_id}/archive")
async def archive_employee(
    emp_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    controller: EmployeeController = Depends(),
) -> dict[str, Any]:
    """Pengarsipan (penghapusan lunak) karyawan yang telah dinonaktifkan."""
    return await controller.handle_archive(current_user, emp_id)


@router.post("/{emp_id}/restore")
async def restore_employee(
    emp_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    controller: EmployeeController = Depends(),
) -> dict[str, Any]:
    """Memulihkan karyawan terhapus sebagai nonaktif."""
    return await controller.handle_restore(current_user, emp_id)


@router.get("/{emp_id}/conflicts")
async def check_conflicts(
    emp_id: UUID,
    start_date: date,
    end_date: date,
    exclude_plan: UUID | None = None,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    controller: EmployeeController = Depends(),
) -> dict[str, Any]:
    """Mengecek konflik jadwal penugasan karyawan."""
    return await controller.handle_check_conflicts(current_user, emp_id, start_date, end_date, exclude_plan)


@router.get("/{emp_id}/emergency-contacts", response_model=list[EmergencyContactResponse])
async def list_emergency_contacts(
    emp_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_USERS)),
    controller: EmployeeController = Depends(),
) -> list[EmergencyContactResponse]:
    """Daftar kontak darurat karyawan (M2-01)."""
    return await controller.handle_list_emergency_contacts(current_user, emp_id)


@router.post(
    "/{emp_id}/emergency-contacts",
    response_model=EmergencyContactResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_emergency_contact(
    emp_id: UUID,
    data: EmergencyContactCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_USERS)),
    controller: EmployeeController = Depends(),
) -> EmergencyContactResponse:
    """Menambahkan kontak darurat baru."""
    return await controller.handle_create_emergency_contact(current_user, emp_id, data)


@router.put("/{emp_id}/emergency-contacts/{contact_id}", response_model=EmergencyContactResponse)
async def update_emergency_contact(
    emp_id: UUID,
    contact_id: UUID,
    data: EmergencyContactUpdate,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_USERS)),
    controller: EmployeeController = Depends(),
) -> EmergencyContactResponse:
    """Mengubah kontak darurat."""
    return await controller.handle_update_emergency_contact(current_user, emp_id, contact_id, data)


@router.delete("/{emp_id}/emergency-contacts/{contact_id}")
async def delete_emergency_contact(
    emp_id: UUID,
    contact_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_USERS)),
    controller: EmployeeController = Depends(),
) -> dict[str, Any]:
    """Menghapus kontak darurat."""
    return await controller.handle_delete_emergency_contact(current_user, emp_id, contact_id)
