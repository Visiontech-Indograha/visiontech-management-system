"""
app/crud/crud_site.py
Lokasi kerja (R-33): `unit_id` NULL = lokasi kantor (Finance), terisi = lokasi proyek unit itu (PM).
Kolom PostGIS tidak keluar mentah — selalu `lat`/`lng`.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDSite(CRUDBase):

    async def viewer(self, user_id: UUID | str) -> Any:
        """Jenis pekerja & unit karyawan akun, serta unit yang dipegang bila PM."""
        return await self.fetchone(
            """
            SELECT e.attendance_mode, e.unit_id AS employee_unit_id,
                   (SELECT r.unit_id FROM vms.user_role r
                    WHERE r.user_id = u.id AND r.role = 'PM' AND r.unit_id IS NOT NULL LIMIT 1) AS pm_unit_id
            FROM vms.app_user u LEFT JOIN vms.employee e ON e.id = u.employee_id
            WHERE u.id = CAST(:uid AS uuid)
            """,
            {"uid": str(user_id)},
        )

    async def list_visible(self, org_id: UUID | str, *, all_sites: bool, office: bool,
                           unit_id: UUID | str | None) -> list[Any]:
        return list(await self.fetchall(
            """
            SELECT s.id, s.name, s.address, s.radius_m, s.unit_id,
                   ST_Y(s.location::geometry) AS lat, ST_X(s.location::geometry) AS lng
            FROM vms.site s
            WHERE s.organization_id = CAST(:org AS uuid) AND s.deleted_at IS NULL
              AND (CAST(:all AS boolean)
                   OR (CAST(:office AS boolean) AND s.unit_id IS NULL)
                   OR (CAST(:unit AS uuid) IS NOT NULL AND s.unit_id = CAST(:unit AS uuid)))
            ORDER BY s.unit_id IS NOT NULL, s.name
            """,
            {"org": str(org_id), "all": all_sites, "office": office,
             "unit": str(unit_id) if unit_id else None},
        ))

    async def insert(self, org_id: UUID | str, *, name: str, address: str | None, radius_m: int,
                     lat: float, lng: float, unit_id: UUID | str | None) -> Any:
        return await self.fetchone(
            """
            INSERT INTO vms.site (organization_id, name, address, radius_m, location, unit_id)
            VALUES (:org, :name, :addr, :rad, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), :unit)
            RETURNING id, name, address, radius_m, unit_id,
                      ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lng
            """,
            {"org": str(org_id), "name": name, "addr": address, "rad": radius_m, "lng": lng, "lat": lat,
             "unit": str(unit_id) if unit_id else None},
        )

    async def get(self, site_id: UUID | str, org_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT s.id, s.name, s.address, s.radius_m, s.unit_id,
                   ST_Y(s.location::geometry) AS lat, ST_X(s.location::geometry) AS lng
            FROM vms.site s
            WHERE s.id = CAST(:id AS uuid) AND s.organization_id = CAST(:org AS uuid) AND s.deleted_at IS NULL
            """,
            {"id": str(site_id), "org": str(org_id)},
        )

    async def archive(self, site_id: UUID | str) -> None:
        await self.execute("UPDATE vms.site SET deleted_at = now() WHERE id = CAST(:id AS uuid)",
                           {"id": str(site_id)})
