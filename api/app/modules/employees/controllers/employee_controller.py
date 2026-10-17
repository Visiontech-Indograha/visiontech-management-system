"""
app/modules/employees/controllers/employee_controller.py

Controller orkestrasi use case manajemen karyawan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException

from app.api.deps import get_employee_service
from app.core.errors import AppError
from app.core.permissions import Permission
from app.core.security import CurrentUser
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
from app.modules.employees.services.employee_service import EmployeeService

PRIVATE_FIELDS = ("email", "phone", "address", "birth_date", "emergency_contact")


def _shown(emp: EmployeeResponse, scope: tuple[bool, str | None]) -> EmployeeResponse:
    """M2-01: data kontak pribadi dikosongkan kecuali untuk HR/admin atau pemiliknya."""
    see_all, own = scope
    if see_all or str(emp.id) == own:
        return emp
    return emp.model_copy(update=dict.fromkeys(PRIVATE_FIELDS))


class EmployeeController:
    """
    Controller use case data karyawan, penempatan, dan mutasi.
    """

    def __init__(self, employee_service: EmployeeService = Depends(get_employee_service)) -> None:
        self.employee_service = employee_service

    async def handle_list_employees(
        self,
        current_user: CurrentUser,
        page: int,
        size: int,
        is_active: bool | None,
        q: str | None,
    ) -> EmployeeListResponse:
        """Mengambil daftar karyawan dengan paginasi dan filter privasi."""
        total, rows = await self.employee_service.list_page(current_user.organization_id, is_active, q, page, size)
        scope = await self.employee_service.private_viewer(current_user.user_id, current_user.permissions)
        items = [_shown(EmployeeResponse(**row._mapping), scope) for row in rows]
        return EmployeeListResponse(items=items, total=total, page=page, size=size)

    async def handle_get_employee(self, current_user: CurrentUser, emp_id: UUID) -> EmployeeResponse:
        """Mengambil detail satu karyawan dengan kontrol akses data pribadi."""
        row = await self.employee_service.get(emp_id, current_user.organization_id)
        scope = await self.employee_service.private_viewer(current_user.user_id, current_user.permissions)
        return _shown(EmployeeResponse(**row._mapping), scope)

    async def handle_create_employee(self, current_user: CurrentUser, data: EmployeeCreate) -> EmployeeResponse:
        """Menambahkan karyawan baru ke dalam organisasi."""
        try:
            row = await self.employee_service.create(current_user.organization_id, data.model_dump())
        except AppError:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": str(e)}) from e
        return EmployeeResponse(
            **data.model_dump(),
            id=row.id,
            is_active=row.is_active,
            offboarded_at=row.offboarded_at,
            offboarding_reason=row.offboarding_reason,
        )

    async def handle_update_employee(
        self, current_user: CurrentUser, emp_id: UUID, data: EmployeeUpdate
    ) -> EmployeeResponse:
        """Mengubah data pribadi karyawan."""
        fields = {
            k: v for k, v in data.model_dump(exclude_unset=True).items() if not (k == "attendance_mode" and v is None)
        }
        if not fields:
            raise HTTPException(
                status_code=400,
                detail={"code": "NO_UPDATE", "message": "Tidak ada data untuk diubah."},
            )
        row = await self.employee_service.update(emp_id, current_user.organization_id, fields)
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"code": "NOT_FOUND", "message": "Karyawan tidak ditemukan."},
            )
        return EmployeeResponse(**row._mapping)

    async def handle_list_assignments(
        self, current_user: CurrentUser, emp_id: UUID
    ) -> list[EmployeeAssignmentResponse]:
        """Mengambil riwayat penempatan atau mutasi jabatan karyawan."""
        rows = await self.employee_service.assignments(emp_id, current_user.organization_id)
        return [EmployeeAssignmentResponse(**r._mapping) for r in rows]

    async def handle_add_assignment(
        self, current_user: CurrentUser, emp_id: UUID, data: EmployeeAssignmentCreate
    ) -> EmployeeAssignmentResponse:
        """Menambahkan penempatan atau promosi baru bagi karyawan."""
        await self.employee_service.ensure_units(current_user.organization_id, data.unit_id)
        row = await self.employee_service.promote(
            emp_id, current_user.organization_id, data.position, data.unit_id, data.valid_from
        )
        return EmployeeAssignmentResponse(**row._mapping)

    async def handle_offboard(self, current_user: CurrentUser, emp_id: UUID, data: EmployeeOffboard) -> dict[str, Any]:
        """Mengakhiri masa kerja karyawan."""
        return await self.employee_service.offboard(emp_id, current_user.organization_id, data.reason)

    async def handle_archive(self, current_user: CurrentUser, emp_id: UUID) -> dict[str, Any]:
        """Menghapus lunak karyawan yang sudah dinonaktifkan."""
        return await self.employee_service.archive_employee(emp_id, current_user.organization_id)

    async def handle_restore(self, current_user: CurrentUser, emp_id: UUID) -> dict[str, Any]:
        """Memulihkan karyawan terhapus menjadi nonaktif."""
        return await self.employee_service.restore_employee(emp_id, current_user.organization_id)

    async def handle_check_conflicts(
        self,
        current_user: CurrentUser,
        emp_id: UUID,
        start_date: date,
        end_date: date,
        exclude_plan: UUID | None,
    ) -> dict[str, Any]:
        """Mengecek konflik jadwal penugasan karyawan."""
        rows = await self.employee_service.conflicts(
            emp_id, current_user.organization_id, start_date, end_date, exclude_plan
        )
        conflicts = [{"id": r.work_plan_id, "number": r.number, "title": r.title} for r in rows]
        return {"conflicts": conflicts, "has_conflict": len(conflicts) > 0}

    async def handle_list_emergency_contacts(
        self, current_user: CurrentUser, emp_id: UUID
    ) -> list[EmergencyContactResponse]:
        """Mengambil daftar kontak darurat karyawan (M2-01)."""
        scope = await self.employee_service.private_viewer(current_user.user_id, current_user.permissions)
        see_all, own = scope
        if not (see_all or str(emp_id) == own):
            return []
        rows = await self.employee_service.list_emergency_contacts(emp_id, current_user.organization_id)
        return [EmergencyContactResponse(**r._mapping) for r in rows]

    async def handle_create_emergency_contact(
        self, current_user: CurrentUser, emp_id: UUID, data: EmergencyContactCreate
    ) -> EmergencyContactResponse:
        """Menambahkan kontak darurat baru."""
        scope = await self.employee_service.private_viewer(current_user.user_id, current_user.permissions)
        _, own = scope
        can_manage = Permission.MANAGE_USERS.value in current_user.permissions
        if not (can_manage or str(emp_id) == own):
            raise HTTPException(
                status_code=403,
                detail="Tidak memiliki izin untuk menambah kontak darurat.",
            )
        row = await self.employee_service.create_emergency_contact(
            emp_id, current_user.organization_id, data.model_dump()
        )
        return EmergencyContactResponse(**row._mapping)

    async def handle_update_emergency_contact(
        self, current_user: CurrentUser, emp_id: UUID, contact_id: UUID, data: EmergencyContactUpdate
    ) -> EmergencyContactResponse:
        """Mengubah kontak darurat."""
        scope = await self.employee_service.private_viewer(current_user.user_id, current_user.permissions)
        _, own = scope
        can_manage = Permission.MANAGE_USERS.value in current_user.permissions
        if not (can_manage or str(emp_id) == own):
            raise HTTPException(
                status_code=403,
                detail="Tidak memiliki izin untuk mengubah kontak darurat.",
            )
        fields = data.model_dump(exclude_unset=True)
        if not fields:
            raise HTTPException(
                status_code=400, detail={"code": "NO_UPDATE", "message": "Tidak ada data untuk diubah."}
            )
        row = await self.employee_service.update_emergency_contact(
            emp_id, contact_id, current_user.organization_id, fields
        )
        return EmergencyContactResponse(**row._mapping)

    async def handle_delete_emergency_contact(
        self, current_user: CurrentUser, emp_id: UUID, contact_id: UUID
    ) -> dict[str, Any]:
        """Menghapus kontak darurat."""
        scope = await self.employee_service.private_viewer(current_user.user_id, current_user.permissions)
        _, own = scope
        can_manage = Permission.MANAGE_USERS.value in current_user.permissions
        if not (can_manage or str(emp_id) == own):
            raise HTTPException(
                status_code=403,
                detail="Tidak memiliki izin untuk menghapus kontak darurat.",
            )
        await self.employee_service.delete_emergency_contact(emp_id, contact_id, current_user.organization_id)
        return {"message": "Kontak darurat berhasil dihapus."}
