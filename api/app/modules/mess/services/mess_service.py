"""
app/modules/mess/services/mess_service.py
Hunian mess karyawan proyek (Milestone 5). Karyawan aktif; tanggal selesai ≥ mulai; tidak boleh tumpang tindih
dengan hunian lain milik karyawan yang sama. Lihat: view:mess; kelola: manage:mess (HR/GA).
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError, ValidationError
from app.modules.mess.repositories.mess_repository import MessRepository
from app.modules.mess.schemas.mess_schema import MessStayCreate, MessStayUpdate


class MessService:
    """Use case akomodasi mess."""

    def __init__(self, db: AsyncSession) -> None:
        self.repo = MessRepository(db)

    async def list_stays(self, employee_id: UUID | None, start: date | None, end: date | None) -> list[Any]:
        return await self.repo.list_stays(employee_id, start, end)

    async def get_stay(self, mess_stay_id: UUID) -> Any:
        stay = await self.repo.get(mess_stay_id)
        if stay is None:
            raise NotFoundError("Hunian mess")
        return stay

    async def _check_period(self, employee_id: UUID, start: date, end: date, exclude: UUID | None = None) -> None:
        if end < start:
            raise ValidationError("Tanggal selesai menginap tidak boleh sebelum tanggal mulai.")
        if await self.repo.overlaps(employee_id, start, end, exclude):
            raise AppError("MESS_OVERLAP", "Karyawan ini sudah tercatat menginap di mess pada tanggal tersebut.",
                           status=409)

    async def create_stay(self, data: MessStayCreate) -> Any:
        if not await self.repo.employee_active(data.employee_id):
            raise ValidationError("Karyawan tidak ditemukan atau tidak aktif.")
        await self._check_period(data.employee_id, data.stay_start_date, data.stay_end_date)
        fields = data.model_dump()
        fields["employee_id"] = str(data.employee_id)
        return await self.repo.get(await self.repo.insert(fields))

    async def update_stay(self, mess_stay_id: UUID, data: MessStayUpdate) -> Any:
        stay = await self.get_stay(mess_stay_id)
        await self._check_period(stay.employee_id, data.stay_start_date or stay.stay_start_date,
                                 data.stay_end_date or stay.stay_end_date, exclude=mess_stay_id)
        await self.repo.update(mess_stay_id, data.model_dump())
        return await self.repo.get(mess_stay_id)

    async def delete_stay(self, mess_stay_id: UUID) -> None:
        await self.get_stay(mess_stay_id)
        await self.repo.archive(mess_stay_id)
