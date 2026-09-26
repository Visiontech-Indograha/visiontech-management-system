"""
app/repositories/plan_location_repo.py
Titik lokasi penugasan SK (revisi PM 2026-09-26). Setiap penetapan membuat baris `site` baru
lalu menautkannya ke SK — site lama tidak diubah agar riwayat absensi (jarak & radius saat itu)
tetap sah.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base_repo import BaseRepo


class PlanLocationRepo(BaseRepo):

    async def site(self, site_id: UUID | str, org_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT id, name, address, radius_m,
                   ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lng
            FROM vms.site
            WHERE id = CAST(:id AS uuid) AND organization_id = CAST(:org AS uuid)
            """,
            {"id": site_id, "org": org_id})

    async def create_site(self, org_id: UUID | str, name: str, address: str | None,
                          lat: float, lng: float, radius_m: int) -> Any:
        return await self.fetchone(
            """
            INSERT INTO vms.site (organization_id, name, address, radius_m, location)
            VALUES (CAST(:org AS uuid), :name, :address, :radius,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography)
            RETURNING id
            """,
            {"org": org_id, "name": name, "address": address, "radius": radius_m, "lat": lat, "lng": lng})

    async def set_plan_site(self, plan_id: UUID | str, site_id: UUID | str) -> None:
        await self.execute(
            """
            UPDATE vms.work_plan SET site_id = CAST(:site AS uuid)
            WHERE id = CAST(:plan AS uuid) AND deleted_at IS NULL
            """,
            {"plan": plan_id, "site": site_id})
