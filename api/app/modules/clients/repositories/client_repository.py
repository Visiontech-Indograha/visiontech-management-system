"""client 1─N project."""
from __future__ import annotations

from typing import Any
from uuid import UUID

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
            """,
            {"q": escape_like(q), "active": active_only},
        ))

    async def get(self, client_id: UUID | str) -> Any:
        return await self.fetchone(_SELECT + " WHERE c.client_id = CAST(:id AS uuid) AND c.delete_at IS NULL",
                                   {"id": str(client_id)})

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
