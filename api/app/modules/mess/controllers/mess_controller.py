"""
app/modules/mess/controllers/mess_controller.py
Controller orkestrasi use case hunian mess karyawan.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.mess.dependencies import get_mess_service
from app.modules.mess.schemas.mess_schema import (
    MessStayCreate,
    MessStayOut,
    MessStayUpdate,
)
from app.modules.mess.services.mess_service import MessService


class MessController:
    """Controller pengelolaan akomodasi mess karyawan."""

    def __init__(self, mess_service: MessService = Depends(get_mess_service)) -> None:
        self.service = mess_service

    async def handle_list_stays(
        self,
        current_user: CurrentUser,
        employee_id: UUID | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list[MessStayOut]:
        rows = await self.service.list_stays(employee_id, start, end)
        return [MessStayOut(**dict(r._mapping)) for r in rows]

    async def handle_get_stay(
        self,
        current_user: CurrentUser,
        mess_stay_id: UUID,
    ) -> MessStayOut:
        row = await self.service.get_stay(mess_stay_id)
        return MessStayOut(**dict(row._mapping))

    async def handle_create_stay(
        self,
        current_user: CurrentUser,
        data: MessStayCreate,
    ) -> MessStayOut:
        row = await self.service.create_stay(data)
        return MessStayOut(**dict(row._mapping))

    async def handle_update_stay(
        self,
        current_user: CurrentUser,
        mess_stay_id: UUID,
        data: MessStayUpdate,
    ) -> MessStayOut:
        row = await self.service.update_stay(mess_stay_id, data)
        return MessStayOut(**dict(row._mapping))

    async def handle_delete_stay(
        self,
        current_user: CurrentUser,
        mess_stay_id: UUID,
    ) -> dict[str, str]:
        await self.service.delete_stay(mess_stay_id)
        return {"message": "Data hunian mess berhasil dihapus."}

    async def handle_my_stays(self, current_user: CurrentUser) -> list[MessStayOut]:
        if current_user.employee_id is None:
            return []
        rows = await self.service.list_stays(UUID(str(current_user.employee_id)), None, None)
        return [MessStayOut(**dict(r._mapping)) for r in rows]
