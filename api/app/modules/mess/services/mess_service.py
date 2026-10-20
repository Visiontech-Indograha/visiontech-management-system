"""
app/modules/mess/services/mess_service.py
Service logika bisnis untuk hunian mess karyawan proyek.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.modules.mess.repositories.mess_repository import MessRepository
from app.modules.mess.schemas.mess_schema import MessStayCreate, MessStayUpdate


class MessService:
    """Service use case akomodasi mess karyawan."""

    def __init__(self, db: AsyncSession) -> None:
        self.repo = MessRepository(db)

    async def list_stays(self, employee_id: UUID | None = None, weekly_plan_id: UUID | None = None) -> Sequence[Any]:
        return await self.repo.list_stays(employee_id, weekly_plan_id)

    async def get_stay(self, mess_stay_id: UUID) -> Any:
        stay = await self.repo.get_stay_by_id(mess_stay_id)
        if not stay:
            raise NotFoundError("Data hunian mess tidak ditemukan.")
        return stay

    async def create_stay(self, data: MessStayCreate) -> Any:
        if data.stay_end_date < data.stay_start_date:
            raise ValidationError("Tanggal selesai menginap tidak boleh sebelum tanggal mulai.")
        return await self.repo.create_stay(data)

    async def update_stay(self, mess_stay_id: UUID, data: MessStayUpdate) -> Any:
        stay = await self.repo.update_stay(mess_stay_id, data)
        if not stay:
            raise NotFoundError("Data hunian mess tidak ditemukan.")
        return stay

    async def delete_stay(self, mess_stay_id: UUID) -> None:
        await self.repo.delete_stay(mess_stay_id)
