"""
app/crud/crud_site.py
Master Kantor Pusat & Kantor Cabang dari tabel office (Master Schema V2).
Koordinat disimpan langsung dalam latitude dan longitude numerik standar.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository


class SiteRepository(BaseRepository):
    """Repositori akses data lokasi kantor dan site operasional (tabel office)."""
    """
    CRUD untuk mengelola master lokasi kantor dan site operasional (tabel office).
    """

    async def viewer(self, user_id: UUID | str) -> Any:
        """
        Mengambil profil pengguna, kantor asal, dan divisi yang dipimpin (jika user adalah Project Manager).
        """
        return await self.fetchone(
            """
            SELECT
                u.system_role::text AS role,
                e.office_id AS employee_unit_id,
                d.division_id AS pm_unit_id,
                CASE
                    WHEN u.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER', 'ADMIN_HR_GA') THEN 'OFFICE'
                    ELSE 'BOTH'
                END AS attendance_mode
            FROM users u
            LEFT JOIN employee e ON e.employee_id = u.employee_id AND e.delete_at IS NULL
            LEFT JOIN division d ON d.pm_id = e.employee_id AND d.delete_at IS NULL
            WHERE u.user_id = CAST(:uid AS uuid) AND u.delete_at IS NULL
            """,
            {"uid": str(user_id)},
        )

    async def list_visible(
        self,
        org_id: UUID | str,
        *,
        all_sites: bool = True,
        office: bool = True,
        unit_id: UUID | str | None = None,
    ) -> list[Any]:
        """
        Mengambil daftar kantor dan site aktif dari tabel office.
        """
        return list(
            await self.fetchall(
                """
                SELECT
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
                FROM office o
                WHERE o.delete_at IS NULL
                ORDER BY o.is_main_office DESC, o.name ASC
                """,
                {},
            )
        )

    async def insert(
        self,
        org_id: UUID | str,
        *,
        name: str,
        address: str | None,
        radius_m: int,
        lat: float,
        lng: float,
        unit_id: UUID | str | None = None,
    ) -> Any:
        """
        Membuat kantor cabang / lokasi kerja baru.
        """
        return await self.fetchone(
            """
            INSERT INTO office (
                name, address, attendance_radius_m, latitude, longitude, is_main_office
            )
            VALUES (
                :name, :addr, :rad, :lat, :lng, FALSE
            )
            RETURNING
                office_id AS id, name, address, attendance_radius_m AS radius_m,
                latitude::float AS lat, longitude::float AS lng, NULL::uuid AS unit_id
            """,
            {
                "name": name,
                "addr": address or "",
                "rad": radius_m,
                "lat": lat,
                "lng": lng,
            },
        )

    async def get(self, site_id: UUID | str, org_id: UUID | str) -> Any:
        """
        Mengambil detail satu lokasi kantor berdasarkan office_id.
        """
        return await self.fetchone(
            """
            SELECT
                o.office_id AS id,
                o.name,
                o.address,
                o.attendance_radius_m AS radius_m,
                NULL::uuid AS unit_id,
                o.latitude::float AS lat,
                o.longitude::float AS lng,
                o.is_main_office
            FROM office o
            WHERE o.office_id = CAST(:id AS uuid) AND o.delete_at IS NULL
            """,
            {"id": str(site_id)},
        )

    async def archive(self, site_id: UUID | str) -> None:
        """
        Melakukan soft-delete (arsip) terhadap kantor cabang (kantor utama dilindungi).
        """
        await self.execute(
            """
            UPDATE office
            SET delete_at = now()
            WHERE office_id = CAST(:id AS uuid) AND is_main_office = FALSE AND delete_at IS NULL
            """,
            {"id": str(site_id)},
        )


# Alias backward compatibility
CRUDSite = SiteRepository
