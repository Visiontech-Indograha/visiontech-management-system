"""
app/modules/employees/controllers/employee_controller.py
Controller karyawan V2 (Milestone 10).
"""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.employees.dependencies import get_employee_service
from app.modules.employees.schemas.employee_schema import (
    AddressIn,
    AddressOut,
    EmployeeCreate,
    EmployeeDetail,
    EmployeeListResponse,
    EmployeeOut,
    EmployeeUpdate,
    MyPhotoIn,
    MyPhotoOut,
    NextEmployeeNo,
)
from app.modules.employees.services.employee_service import EmployeeService


class EmployeeController:
    def __init__(self, employee_service: EmployeeService = Depends(get_employee_service)) -> None:
        self.service = employee_service

    async def list(self, *, user: CurrentUser, page: int, size: int, status: str | None, division_id: UUID | None,
                   office_id: UUID | None, position_id: UUID | None, q: str | None) -> EmployeeListResponse:
        rows, total = await self.service.list(page=page, size=size, status=status, division_id=division_id,
                                              office_id=office_id, position_id=position_id, q=q, user=user)
        return EmployeeListResponse(items=[EmployeeOut(**r) for r in rows], total=total, page=page, size=size)

    async def detail(self, user: CurrentUser, employee_id: UUID) -> EmployeeDetail:
        return EmployeeDetail(**await self.service.detail(employee_id, user))

    async def next_no(self) -> NextEmployeeNo:
        return NextEmployeeNo(employee_no=await self.service.next_employee_no())

    async def create(self, data: EmployeeCreate, user: CurrentUser | None = None) -> EmployeeDetail:
        return EmployeeDetail(**await self.service.create(data, user))

    async def update(self, employee_id: UUID, data: EmployeeUpdate, user: CurrentUser | None = None) -> EmployeeDetail:
        return EmployeeDetail(**await self.service.update(employee_id, data, user))

    async def set_my_photo(self, user: CurrentUser, data: MyPhotoIn) -> MyPhotoOut:
        return MyPhotoOut(photo_file_id=await self.service.set_own_photo(user, data.file_id))

    async def add_address(self, employee_id: UUID, data: AddressIn) -> AddressOut:
        return AddressOut(**dict((await self.service.add_address(employee_id, data))._mapping))

    async def update_address(self, employee_id: UUID, address_id: UUID, data: AddressIn) -> AddressOut:
        return AddressOut(**dict((await self.service.update_address(employee_id, address_id, data))._mapping))

    async def delete_address(self, employee_id: UUID, address_id: UUID) -> dict[str, str]:
        await self.service.delete_address(employee_id, address_id)
        return {"message": "Alamat dihapus."}

    async def archive(self, employee_id: UUID) -> dict[str, str]:
        return await self.service.archive(employee_id)

    async def delete(self, employee_id: UUID, actor: CurrentUser) -> dict[str, str]:
        await self.service.delete(employee_id, actor)
        return {"status": "deleted"}

    async def restore(self, employee_id: UUID) -> dict[str, str]:
        return await self.service.restore(employee_id)
