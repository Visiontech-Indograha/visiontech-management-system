"""
app/modules/work_plans/repositories/plan_location_repository.py
Titik lokasi penugasan rencana kerja Master Schema V2 (tabel office & work_plan_daily).
Koordinat disimpan langsung dalam latitude dan longitude numerik standar tanpa dependensi PostGIS.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import CRUDBase


class CRUDPlanLocation(CRUDBase):
    """
    CRUD untuk mengelola titik lokasi kantor dan site rencana kerja (Master Schema V2).
    """

    async def site(self, site_id: UUID | str, org_id: UUID | str) -> Any:
        """
        Mengambil informasi detail sebuah site/kantor.
        """
        return await self.fetchone(
            """
            SELECT office_id AS id, name, address, attendance_radius_m AS radius_m,
                   latitude::float AS lat, longitude::float AS lng
            FROM office
            WHERE office_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {"id": str(site_id)},
        )

    async def names_like(self, org_id: UUID | str, name: str) -> set[str]:
        """
        Mencari nama-nama lokasi (kantor/site) yang diawali dengan string tertentu.
        """
        rows = await self.fetchall(
            """
            SELECT name FROM office
            WHERE delete_at IS NULL AND left(name, char_length(:name)) = :name
            """,
            {"name": name},
        )
        return {r.name for r in rows}

    async def same_site(self, org_id: UUID | str, label: str, lat: float, lng: float, radius_m: int) -> Any:
        """
        Mencari site yang memiliki label dan titik koordinat berdekatan tanpa duplikasi.
        """
        return await self.fetchone(
            """
            SELECT office_id AS id FROM office
            WHERE attendance_radius_m = :radius
              AND (name = :name OR name LIKE :name || ' (%)')
              AND delete_at IS NULL
              AND abs(latitude - CAST(:lat AS numeric(10,7))) < 0.0001
              AND abs(longitude - CAST(:lng AS numeric(10,7))) < 0.0001
            ORDER BY char_length(name), name
            LIMIT 1
            """,
            {"name": label, "radius": radius_m, "lat": lat, "lng": lng},
        )

    async def create_site(
        self, org_id: UUID | str, name: str, address: str | None, lat: float, lng: float, radius_m: int
    ) -> Any:
        """
        Membuat record site/kantor baru.
        """
        return await self.fetchone(
            """
            INSERT INTO office (
                name, address, latitude, longitude, attendance_radius_m, is_main_office
            )
            VALUES (
                :name, COALESCE(:address, :name), CAST(:lat AS numeric(10,7)),
                CAST(:lng AS numeric(10,7)), :radius, FALSE
            )
            RETURNING office_id AS id
            """,
            {"name": name, "address": address, "radius": radius_m, "lat": lat, "lng": lng},
        )

    async def set_plan_site(self, plan_id: UUID | str, site_id: UUID | str) -> None:
        """
        Menetapkan atau memperbarui site yang digunakan oleh sebuah rencana kerja (work_plan_daily).
        """
        await self.execute(
            """
            UPDATE work_plan_daily
            SET site_name = COALESCE((SELECT name FROM office WHERE office_id = CAST(:site AS uuid)), site_name),
                site_lat = COALESCE((SELECT latitude FROM office WHERE office_id = CAST(:site AS uuid)), site_lat),
                site_lng = COALESCE((SELECT longitude FROM office WHERE office_id = CAST(:site AS uuid)), site_lng),
                attendance_radius_m = COALESCE(
                    (SELECT attendance_radius_m FROM office WHERE office_id = CAST(:site AS uuid)),
                    attendance_radius_m
                ),
                update_at = now()
            WHERE weekly_plan_id = CAST(:plan AS uuid) AND delete_at IS NULL
            """,
            {"plan": str(plan_id), "site": str(site_id)},
        )
