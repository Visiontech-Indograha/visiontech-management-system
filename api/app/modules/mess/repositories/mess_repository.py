"""
app/modules/mess/repositories/mess_repository.py
Hunian mess karyawan (company_mess_stay N─1 employee), berbasis rentang tanggal riil (daily-first: tanpa tautan
ke rencana mingguan).
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_SELECT = """
    SELECT m.mess_stay_id, m.mess_name, m.city, m.address, m.latitude, m.longitude, m.employee_id,
           e.full_name AS employee_name, e.employee_no, m.stay_start_date, m.stay_end_date, m.create_at
    FROM company_mess_stay m
    JOIN employee e ON e.employee_id = m.employee_id
"""


class MessRepository(BaseRepository):
    """Query company_mess_stay."""

    async def list_stays(self, employee_id: UUID | None, start: date | None, end: date | None) -> list[Any]:
        """Hunian yang beririsan dengan rentang [start, end] (mis. minggu jadwal)."""
        return list(await self.fetchall(
            _SELECT + """
            WHERE m.delete_at IS NULL
              AND (CAST(:emp AS uuid) IS NULL OR m.employee_id = CAST(:emp AS uuid))
              AND (CAST(:end AS date) IS NULL OR m.stay_start_date <= CAST(:end AS date))
              AND (CAST(:start AS date) IS NULL OR m.stay_end_date >= CAST(:start AS date))
            ORDER BY m.stay_start_date DESC, e.full_name
            """,
            {"emp": str(employee_id) if employee_id else None, "start": start, "end": end},
        ))

    async def get(self, mess_stay_id: UUID | str) -> Any:
        return await self.fetchone(
            _SELECT + " WHERE m.mess_stay_id = CAST(:id AS uuid) AND m.delete_at IS NULL", {"id": str(mess_stay_id)}
        )

    async def employee_active(self, employee_id: UUID | str) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM employee WHERE employee_id = CAST(:id AS uuid) AND delete_at IS NULL "
            "AND offboarding_status = 'active')",
            {"id": str(employee_id)},
        ))

    async def overlaps(
        self, employee_id: UUID | str, start: date, end: date, exclude: UUID | str | None = None
    ) -> bool:
        """Satu karyawan tidak menginap di dua mess pada tanggal yang sama."""
        return bool(await self.scalar(
            """
            SELECT EXISTS (SELECT 1 FROM company_mess_stay WHERE employee_id = CAST(:emp AS uuid)
                           AND delete_at IS NULL AND stay_start_date <= :end AND stay_end_date >= :start
                           AND (CAST(:ex AS uuid) IS NULL OR mess_stay_id <> CAST(:ex AS uuid)))
            """,
            {"emp": str(employee_id), "start": start, "end": end, "ex": str(exclude) if exclude else None},
        ))

    async def insert(self, fields: dict[str, Any]) -> UUID:
        stay_id: UUID = await self.scalar(
            """
            INSERT INTO company_mess_stay (mess_name, city, address, latitude, longitude, employee_id,
                                           stay_start_date, stay_end_date)
            VALUES (:mess_name, :city, :address, :latitude, :longitude, CAST(:employee_id AS uuid),
                    :stay_start_date, :stay_end_date)
            RETURNING mess_stay_id
            """,
            fields,
        )
        return stay_id

    async def update(self, mess_stay_id: UUID | str, fields: dict[str, Any]) -> None:
        await self.execute(
            """
            UPDATE company_mess_stay SET
                mess_name = COALESCE(:mess_name, mess_name), city = COALESCE(:city, city),
                address = COALESCE(:address, address),
                latitude = COALESCE(CAST(:latitude AS numeric), latitude),
                longitude = COALESCE(CAST(:longitude AS numeric), longitude),
                stay_start_date = COALESCE(CAST(:stay_start_date AS date), stay_start_date),
                stay_end_date = COALESCE(CAST(:stay_end_date AS date), stay_end_date),
                update_at = now()
            WHERE mess_stay_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {**fields, "id": str(mess_stay_id)},
        )

    async def archive(self, mess_stay_id: UUID | str) -> None:
        await self.execute(
            "UPDATE company_mess_stay SET delete_at = now(), update_at = now() "
            "WHERE mess_stay_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(mess_stay_id)},
        )
