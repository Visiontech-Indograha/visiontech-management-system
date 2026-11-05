"""client 1─N project."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.core.list_params import MAX_ROWS_UNPAGED
from app.core.repository import BaseRepository, escape_like, safe_columns

_SELECT = """
    SELECT c.client_id, c.client_code, c.name, c.pic_name, c.pic_phone, c.address, c.status,
           (SELECT COUNT(*) FROM project p WHERE p.client_id = c.client_id AND p.delete_at IS NULL)::int
               AS project_count
    FROM client c
"""


class ClientRepository(BaseRepository):
    async def list(self, q: str | None, active_only: bool) -> list[Any]:
        return list(await self.fetchall(
            _SELECT + """
            WHERE c.delete_at IS NULL AND (NOT CAST(:active AS boolean) OR c.status)
              AND (CAST(:q AS varchar) IS NULL OR c.name ILIKE '%' || CAST(:q AS varchar) || '%'
                   OR c.client_code ILIKE '%' || CAST(:q AS varchar) || '%')
            ORDER BY c.name
            LIMIT :cap
            """,
            {"q": escape_like(q), "active": active_only, "cap": MAX_ROWS_UNPAGED},
        ))

    async def get(self, client_id: UUID | str) -> Any:
        return await self.fetchone(_SELECT + " WHERE c.client_id = CAST(:id AS uuid) AND c.delete_at IS NULL",
                                   {"id": str(client_id)})

    async def manages_via_project(self, client_id: UUID | str, employee_id: str | None) -> bool:
        """Pengguna adalah PM/OM divisi dari salah satu proyek klien ini (proyek belum dihapus)."""
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM project p JOIN division d ON d.division_id = p.division_id "
            "WHERE p.client_id = CAST(:id AS uuid) AND p.delete_at IS NULL "
            "AND CAST(:emp AS uuid) IN (d.pm_id, d.om_id))",
            {"id": str(client_id), "emp": employee_id},
        ))

    async def find_by_name(self, name: str, exclude: UUID | None = None) -> Any:
        """Klien aktif dengan nama yang sama (lower/trim, tanpa memperhatikan huruf besar-kecil)."""
        return await self.fetchone(
            "SELECT client_id, name FROM client WHERE lower(trim(name)) = :name AND delete_at IS NULL "
            "AND (CAST(:ex AS uuid) IS NULL OR client_id <> CAST(:ex AS uuid)) ORDER BY create_at LIMIT 1",
            {"name": name.strip().lower(), "ex": str(exclude) if exclude else None},
        )

    async def code_taken(self, code: str, exclude: UUID | None = None) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM client WHERE lower(client_code) = lower(:code) AND delete_at IS NULL "
            "AND (CAST(:ex AS uuid) IS NULL OR client_id <> CAST(:ex AS uuid)))",
            {"code": code, "ex": str(exclude) if exclude else None},
        ))

    async def insert(self, data: dict[str, Any]) -> Any:
        new_id = await self.scalar(
            "INSERT INTO client (client_code, name, pic_name, pic_phone, address) "
            "VALUES (:client_code, :name, :pic_name, :pic_phone, :address) RETURNING client_id",
            data,
        )
        return await self.get(new_id)

    async def update(self, client_id: UUID, fields: dict[str, Any]) -> Any:
        if fields:
            sets = ", ".join(f"{k} = :{k}" for k in safe_columns(fields))
            await self.execute(f"UPDATE client SET {sets}, update_at = now() WHERE client_id = CAST(:id AS uuid)",
                               {**fields, "id": str(client_id)})
        return await self.get(client_id)

    async def archive(self, client_id: UUID) -> None:
        await self.execute("UPDATE client SET delete_at = now(), update_at = now() WHERE client_id = CAST(:id AS uuid)",
                           {"id": str(client_id)})

    # ── Client Sites ────────────────────────────────────────────────────────
    async def list_sites(self, client_id: UUID | str) -> Sequence[Any]:
        return list(await self.fetchall(
            """
            SELECT site_id, client_id, site_name, address, latitude, longitude,
                   geofence_radius_meters, pic_name, pic_phone
            FROM client_sites
            WHERE client_id = CAST(:cid AS uuid) AND delete_at IS NULL
            ORDER BY site_name
            """,
            {"cid": str(client_id)},
        ))

    async def get_site(self, site_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT site_id, client_id, site_name, address, latitude, longitude,
                   geofence_radius_meters, pic_name, pic_phone
            FROM client_sites
            WHERE site_id = CAST(:sid AS uuid) AND delete_at IS NULL
            """,
            {"sid": str(site_id)},
        )

    async def create_site(self, client_id: UUID | str, data: dict[str, Any]) -> Any:
        site_id = await self.scalar(
            """
            INSERT INTO client_sites (
                client_id, site_name, address, latitude, longitude,
                geofence_radius_meters, pic_name, pic_phone
            )
            VALUES (
                CAST(:client_id AS uuid), :site_name, :address, :latitude, :longitude,
                :geofence_radius_meters, :pic_name, :pic_phone
            )
            RETURNING site_id
            """,
            {**data, "client_id": str(client_id)},
        )
        return await self.get_site(site_id)

    async def update_site(self, site_id: UUID | str, fields: dict[str, Any]) -> Any:
        if fields:
            sets = ", ".join(f"{k} = :{k}" for k in safe_columns(fields))
            await self.execute(
                f"UPDATE client_sites SET {sets}, update_at = now() WHERE site_id = CAST(:sid AS uuid)",
                {**fields, "sid": str(site_id)},
            )
        return await self.get_site(site_id)

    async def delete_site(self, site_id: UUID | str) -> None:
        await self.execute(
            "UPDATE client_sites SET delete_at = now(), update_at = now() WHERE site_id = CAST(:sid AS uuid)",
            {"sid": str(site_id)},
        )

