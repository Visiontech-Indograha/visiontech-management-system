"""
app/modules/offices/repositories/office_repository.py
Master kantor pusat & cabang (tabel `office`, Master Schema V2).

Relasi: office 1─N employee, team, tool, vehicle, attendance. Kantor utama tunggal dijaga indeks unik
`uq_single_main_office`. Penghapusan = soft delete (`delete_at`).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_COLUMNS = """
    o.office_id AS id,
    o.name,
    o.address,
    o.attendance_radius_m AS radius_m,
    NULL::uuid AS unit_id,
    o.latitude::float AS lat,
    o.longitude::float AS lng,
    o.is_main_office,
    o.city_boundary_radius_m,
    o.clock_in_time,
    o.clock_out_time,
    o.in_city_meal_rate,
    o.out_city_meal_rate
"""


class OfficeRepository(BaseRepository):
    """Repositori master kantor (tabel `office`)."""

    async def list_active(self) -> list[Any]:
        """Semua kantor aktif, kantor utama lebih dulu."""
        return list(
            await self.fetchall(
                f"SELECT {_COLUMNS} FROM office o WHERE o.delete_at IS NULL "
                "ORDER BY o.is_main_office DESC, o.name ASC"
            )
        )

    async def get(self, office_id: UUID | str, org_id: UUID | str | None = None) -> Any:
        """Satu kantor aktif."""
        return await self.fetchone(
            f"SELECT {_COLUMNS} FROM office o WHERE o.office_id = CAST(:id AS uuid) AND o.delete_at IS NULL",
            {"id": str(office_id)},
        )

    async def insert(self, data: dict[str, Any]) -> Any:
        """Kantor baru (selalu cabang; penetapan kantor utama lewat `set_main`)."""
        row = await self.fetchone(
            """
            INSERT INTO office (
                name, address, latitude, longitude, attendance_radius_m, city_boundary_radius_m,
                clock_in_time, clock_out_time, in_city_meal_rate, out_city_meal_rate, is_main_office
            ) VALUES (
                :name, :address, :lat, :lng, :radius_m, :city_boundary_radius_m,
                :clock_in_time, :clock_out_time, :in_city_meal_rate, :out_city_meal_rate, FALSE
            )
            RETURNING office_id
            """,
            data,
        )
        return await self.get(row.office_id)

    async def update(self, office_id: UUID | str, data: dict[str, Any]) -> Any:
        """Ubah sebagian kolom kantor; nilai None = tidak diubah."""
        await self.execute(
            """
            UPDATE office SET
                name = COALESCE(:name, name),
                address = COALESCE(:address, address),
                latitude = COALESCE(:lat, latitude),
                longitude = COALESCE(:lng, longitude),
                attendance_radius_m = COALESCE(:radius_m, attendance_radius_m),
                city_boundary_radius_m = COALESCE(:city_boundary_radius_m, city_boundary_radius_m),
                clock_in_time = COALESCE(:clock_in_time, clock_in_time),
                clock_out_time = COALESCE(:clock_out_time, clock_out_time),
                in_city_meal_rate = COALESCE(:in_city_meal_rate, in_city_meal_rate),
                out_city_meal_rate = COALESCE(:out_city_meal_rate, out_city_meal_rate),
                update_at = now()
            WHERE office_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {**data, "id": str(office_id)},
        )
        return await self.get(office_id)

    async def set_main(self, office_id: UUID | str) -> None:
        """Jadikan kantor ini kantor utama (yang lama dilepas lebih dulu — uq_single_main_office)."""
        await self.execute(
            "UPDATE office SET is_main_office = FALSE, update_at = now() "
            "WHERE is_main_office AND office_id <> CAST(:id AS uuid)",
            {"id": str(office_id)},
        )
        await self.execute(
            "UPDATE office SET is_main_office = TRUE, update_at = now() "
            "WHERE office_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(office_id)},
        )

    async def active_employee_count(self, office_id: UUID | str) -> int:
        """Karyawan aktif yang masih berkantor di sini (FK employee.office_id)."""
        return int(
            await self.scalar(
                "SELECT count(*) FROM employee WHERE office_id = CAST(:id AS uuid) AND delete_at IS NULL",
                {"id": str(office_id)},
            )
            or 0
        )

    async def archive(self, office_id: UUID | str) -> None:
        """Soft delete kantor cabang (kantor utama tidak pernah diarsipkan)."""
        await self.execute(
            "UPDATE office SET delete_at = now(), update_at = now() "
            "WHERE office_id = CAST(:id AS uuid) AND is_main_office = FALSE AND delete_at IS NULL",
            {"id": str(office_id)},
        )


CRUDOffice = OfficeRepository
