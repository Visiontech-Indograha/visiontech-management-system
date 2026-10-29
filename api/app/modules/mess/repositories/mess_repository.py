"""
app/modules/mess/repositories/mess_repository.py
Master lokasi mess (company_mess) dan hunian karyawan (company_mess_stay N─1 employee, N─1 company_mess), berbasis
rentang tanggal riil (daily-first: tanpa tautan ke rencana mingguan). Hunian diajukan karyawan (REQUESTED) lalu
diputus PM/OM/HR (APPROVED/REJECTED), atau dicatat langsung oleh HR (APPROVED).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_ACTIVE = ("REQUESTED", "APPROVED")

_SELECT = """
    SELECT m.mess_stay_id, m.mess_id, m.mess_name, m.city, m.address, m.latitude, m.longitude, m.employee_id,
           e.full_name AS employee_name, e.employee_no,
           (SELECT f.id FROM file_object f WHERE f.storage_key = e.profile_photo_path LIMIT 1)
               AS employee_photo_file_id, m.stay_start_date, m.stay_end_date, m.status,
           m.request_note, m.decision_note, m.decided_at, m.create_at
    FROM company_mess_stay m
    JOIN employee e ON e.employee_id = m.employee_id
"""

_PLACE_SELECT = """
    SELECT p.mess_id, p.mess_name, p.city, p.address, p.latitude, p.longitude, p.capacity,
           (SELECT COUNT(*) FROM company_mess_stay s
             WHERE s.mess_id = p.mess_id AND s.delete_at IS NULL AND s.status = 'APPROVED'
               AND s.stay_start_date <= CURRENT_DATE AND s.stay_end_date >= CURRENT_DATE) AS occupied
    FROM company_mess p
"""


class MessRepository(BaseRepository):
    """Query company_mess dan company_mess_stay."""

    # --- master mess ---------------------------------------------------------------------------------------------
    async def list_places(self) -> list[Any]:
        return list(await self.fetchall(_PLACE_SELECT + " WHERE p.delete_at IS NULL ORDER BY p.mess_name"))

    async def get_place(self, mess_id: UUID | str) -> Any:
        return await self.fetchone(
            _PLACE_SELECT + " WHERE p.mess_id = CAST(:id AS uuid) AND p.delete_at IS NULL", {"id": str(mess_id)}
        )

    async def insert_place(self, fields: dict[str, Any]) -> UUID:
        mess_id: UUID = await self.scalar(
            """
            INSERT INTO company_mess (mess_name, city, address, latitude, longitude, capacity)
            VALUES (:mess_name, :city, :address, :latitude, :longitude, :capacity)
            RETURNING mess_id
            """,
            fields,
        )
        return mess_id

    async def update_place(self, mess_id: UUID | str, fields: dict[str, Any]) -> None:
        await self.execute(
            """
            UPDATE company_mess SET
                mess_name = COALESCE(:mess_name, mess_name), city = COALESCE(:city, city),
                address = COALESCE(:address, address),
                latitude = COALESCE(CAST(:latitude AS numeric), latitude),
                longitude = COALESCE(CAST(:longitude AS numeric), longitude),
                capacity = COALESCE(:capacity, capacity), update_at = now()
            WHERE mess_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {**fields, "id": str(mess_id)},
        )

    async def place_has_active_stays(self, mess_id: UUID | str) -> bool:
        return bool(await self.scalar(
            """
            SELECT EXISTS (SELECT 1 FROM company_mess_stay WHERE mess_id = CAST(:id AS uuid) AND delete_at IS NULL
                           AND status = ANY(:active) AND stay_end_date >= CURRENT_DATE)
            """,
            {"id": str(mess_id), "active": list(_ACTIVE)},
        ))

    async def archive_place(self, mess_id: UUID | str) -> None:
        await self.execute(
            "UPDATE company_mess SET delete_at = now(), update_at = now() "
            "WHERE mess_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(mess_id)},
        )

    async def approved_overlap_count(
        self, mess_id: UUID | str, start: date, end: date, exclude: UUID | str | None = None
    ) -> int:
        """Jumlah hunian disetujui yang beririsan di mess itu (batas kapasitas)."""
        return int(await self.scalar(
            """
            SELECT COUNT(*) FROM company_mess_stay WHERE mess_id = CAST(:id AS uuid) AND delete_at IS NULL
              AND status = 'APPROVED' AND stay_start_date <= :end AND stay_end_date >= :start
              AND (CAST(:ex AS uuid) IS NULL OR mess_stay_id <> CAST(:ex AS uuid))
            """,
            {"id": str(mess_id), "start": start, "end": end, "ex": str(exclude) if exclude else None},
        ) or 0)

    # --- hunian ----------------------------------------------------------------------------------------------------
    async def list_stays(
        self, employee_id: UUID | None, start: date | None, end: date | None, status: str | None = None
    ) -> list[Any]:
        """Hunian yang beririsan dengan rentang [start, end] (mis. minggu jadwal)."""
        return list(await self.fetchall(
            _SELECT + """
            WHERE m.delete_at IS NULL
              AND (CAST(:emp AS uuid) IS NULL OR m.employee_id = CAST(:emp AS uuid))
              AND (CAST(:end AS date) IS NULL OR m.stay_start_date <= CAST(:end AS date))
              AND (CAST(:start AS date) IS NULL OR m.stay_end_date >= CAST(:start AS date))
              AND (CAST(:status AS text) IS NULL OR m.status = CAST(:status AS text))
            ORDER BY (m.status = 'REQUESTED') DESC, m.stay_start_date DESC, e.full_name
            """,
            {"emp": str(employee_id) if employee_id else None, "start": start, "end": end, "status": status},
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

    async def division_pm_of(self, employee_id: UUID | str) -> Any:
        """pm_id divisi tempat karyawan bernaung (None bila tanpa divisi)."""
        row = await self.fetchone(
            """
            SELECT d.pm_id FROM employee e LEFT JOIN division d ON d.division_id = e.division_id
            WHERE e.employee_id = CAST(:id AS uuid)
            """,
            {"id": str(employee_id)},
        )
        return row.pm_id if row else None

    async def overlaps(
        self, employee_id: UUID | str, start: date, end: date, exclude: UUID | str | None = None
    ) -> bool:
        """Satu karyawan tidak menginap (atau mengajukan) di dua mess pada tanggal yang sama."""
        return bool(await self.scalar(
            """
            SELECT EXISTS (SELECT 1 FROM company_mess_stay WHERE employee_id = CAST(:emp AS uuid)
                           AND delete_at IS NULL AND status = ANY(:active)
                           AND stay_start_date <= :end AND stay_end_date >= :start
                           AND (CAST(:ex AS uuid) IS NULL OR mess_stay_id <> CAST(:ex AS uuid)))
            """,
            {"emp": str(employee_id), "start": start, "end": end, "active": list(_ACTIVE),
             "ex": str(exclude) if exclude else None},
        ))

    async def insert(self, fields: dict[str, Any]) -> UUID:
        """Salin nama/alamat mess ke baris hunian (riwayat tetap utuh walau master diubah)."""
        stay_id: UUID = await self.scalar(
            """
            INSERT INTO company_mess_stay (mess_id, mess_name, city, address, latitude, longitude, employee_id,
                                           stay_start_date, stay_end_date, status, requested_by_user_id,
                                           request_note, decided_by_user_id, decided_at)
            SELECT p.mess_id, p.mess_name, p.city, p.address, p.latitude, p.longitude, CAST(:employee_id AS uuid),
                   :stay_start_date, :stay_end_date, CAST(:status AS text), CAST(:requested_by AS uuid),
                   :request_note, CAST(:decided_by AS uuid), CAST(:decided_at AS timestamptz)
            FROM company_mess p WHERE p.mess_id = CAST(:mess_id AS uuid) AND p.delete_at IS NULL
            RETURNING mess_stay_id
            """,
            fields,
        )
        return stay_id

    async def decide(
        self, mess_stay_id: UUID | str, status: str, user_id: str, note: str | None, at: datetime
    ) -> None:
        await self.execute(
            """
            UPDATE company_mess_stay SET status = :status, decided_by_user_id = CAST(:uid AS uuid),
                decision_note = :note, decided_at = :at, update_at = now()
            WHERE mess_stay_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {"id": str(mess_stay_id), "status": status, "uid": user_id, "note": note, "at": at},
        )

    async def set_status(self, mess_stay_id: UUID | str, status: str) -> None:
        await self.execute(
            "UPDATE company_mess_stay SET status = :status, update_at = now() "
            "WHERE mess_stay_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(mess_stay_id), "status": status},
        )

    async def set_end_date(self, mess_stay_id: UUID | str, end: date) -> None:
        await self.execute(
            "UPDATE company_mess_stay SET stay_end_date = :end, update_at = now() "
            "WHERE mess_stay_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(mess_stay_id), "end": end},
        )

    async def update_dates(self, mess_stay_id: UUID | str, start: date | None, end: date | None) -> None:
        await self.execute(
            """
            UPDATE company_mess_stay SET
                stay_start_date = COALESCE(CAST(:start AS date), stay_start_date),
                stay_end_date = COALESCE(CAST(:end AS date), stay_end_date), update_at = now()
            WHERE mess_stay_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {"id": str(mess_stay_id), "start": start, "end": end},
        )

    async def archive(self, mess_stay_id: UUID | str) -> None:
        await self.execute(
            "UPDATE company_mess_stay SET delete_at = now(), update_at = now() "
            "WHERE mess_stay_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(mess_stay_id)},
        )
