"""
app/modules/mess/controllers/mess_controller.py
Controller orkestrasi use case mess karyawan: master mess, hunian, pengajuan, dan keputusan.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.mess.dependencies import get_mess_service
from app.modules.mess.schemas.mess_schema import (
    MessDecision,
    MessPlaceIn,
    MessPlaceOut,
    MessPlaceUpdate,
    MessStayCreate,
    MessStayOut,
    MessStayRequest,
    MessStayUpdate,
)
from app.modules.mess.services.mess_service import MessService


def _stay(row: Any) -> MessStayOut:
    return MessStayOut(**dict(row._mapping))


def _place(row: Any) -> MessPlaceOut:
    return MessPlaceOut(**dict(row._mapping))


class MessController:
    """Controller pengelolaan akomodasi mess karyawan."""

    def __init__(self, mess_service: MessService = Depends(get_mess_service)) -> None:
        self.service = mess_service

    # --- master mess ---
    async def handle_list_places(self, current_user: CurrentUser) -> list[MessPlaceOut]:
        return [_place(r) for r in await self.service.list_places()]

    async def handle_create_place(self, current_user: CurrentUser, data: MessPlaceIn) -> MessPlaceOut:
        return _place(await self.service.create_place(data))

    async def handle_update_place(
        self, current_user: CurrentUser, mess_id: UUID, data: MessPlaceUpdate
    ) -> MessPlaceOut:
        return _place(await self.service.update_place(mess_id, data))

    async def handle_delete_place(self, current_user: CurrentUser, mess_id: UUID) -> dict[str, str]:
        await self.service.delete_place(mess_id)
        return {"message": "Mess berhasil dihapus dari daftar."}

    # --- hunian ---
    async def handle_list_stays(
        self,
        current_user: CurrentUser,
        employee_id: UUID | None = None,
        start: date | None = None,
        end: date | None = None,
        status: str | None = None,
    ) -> list[MessStayOut]:
        rows = await self.service.list_stays(employee_id, start, end, status, current_user)
        return [_stay(r) for r in rows]

    async def handle_get_stay(self, current_user: CurrentUser, mess_stay_id: UUID) -> MessStayOut:
        return _stay(await self.service.get_stay(mess_stay_id, current_user))

    async def handle_create_stay(self, current_user: CurrentUser, data: MessStayCreate) -> MessStayOut:
        return _stay(await self.service.create_stay(current_user, data))

    async def handle_request_stay(self, current_user: CurrentUser, data: MessStayRequest) -> MessStayOut:
        return _stay(await self.service.request_stay(current_user, data))

    async def handle_decide(
        self, current_user: CurrentUser, mess_stay_id: UUID, data: MessDecision
    ) -> MessStayOut:
        return _stay(await self.service.decide(current_user, mess_stay_id, data))

    async def handle_cancel(self, current_user: CurrentUser, mess_stay_id: UUID) -> MessStayOut:
        return _stay(await self.service.cancel(current_user, mess_stay_id))

    async def handle_end(self, current_user: CurrentUser, mess_stay_id: UUID) -> MessStayOut:
        return _stay(await self.service.end_stay(current_user, mess_stay_id))

    async def handle_update_stay(
        self, current_user: CurrentUser, mess_stay_id: UUID, data: MessStayUpdate
    ) -> MessStayOut:
        return _stay(await self.service.update_stay(mess_stay_id, data, current_user))

    async def handle_delete_stay(self, current_user: CurrentUser, mess_stay_id: UUID) -> dict[str, str]:
        await self.service.delete_stay(mess_stay_id, current_user)
        return {"message": "Data hunian mess berhasil dihapus."}

    async def handle_my_stays(self, current_user: CurrentUser) -> list[MessStayOut]:
        if current_user.employee_id is None:
            return []
        rows = await self.service.list_stays(UUID(str(current_user.employee_id)), None, None)
        return [_stay(r) for r in rows]
