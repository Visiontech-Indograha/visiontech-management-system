"""job_position N─1 division (opsional); employee N─1 job_position (position_id)."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_SELECT = """
    SELECT p.position_id, p.division_id, d.name AS division_name, p.code, p.name, p.grade_level,
           p.daily_allowance, p.description, p.status,
           (SELECT COUNT(*) FROM employee e WHERE e.position_id = p.position_id AND e.delete_at IS NULL
              AND e.offboarding_status <> 'offboarded')::int AS employee_count
    FROM job_position p LEFT JOIN division d ON d.division_id = p.division_id
"""


class JobPositionRepository(BaseRepository):
    async def list(self, division_id: UUID | None, active_only: bool) -> list[Any]:
        return list(await self.fetchall(
            _SELECT + """
            WHERE p.delete_at IS NULL AND (NOT CAST(:active AS boolean) OR p.status)
              AND (CAST(:div AS uuid) IS NULL OR p.division_id = CAST(:div AS uuid) OR p.division_id IS NULL)
            ORDER BY p.grade_level DESC, p.name
            """,
            {"div": str(division_id) if division_id else None, "active": active_only},
        ))

    async def get(self, position_id: UUID | str) -> Any:
        return await self.fetchone(_SELECT + " WHERE p.position_id = CAST(:id AS uuid) AND p.delete_at IS NULL",
                                   {"id": str(position_id)})

    async def code_taken(self, code: str, exclude: UUID | None = None) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM job_position WHERE lower(code) = lower(:code) AND delete_at IS NULL "
            "AND (CAST(:ex AS uuid) IS NULL OR position_id <> CAST(:ex AS uuid)))",
            {"code": code, "ex": str(exclude) if exclude else None},
        ))

    async def insert(self, data: dict[str, Any]) -> Any:
        new_id = await self.scalar(
            """
            INSERT INTO job_position (division_id, code, name, grade_level, daily_allowance, description)
            VALUES (CAST(:division_id AS uuid), :code, :name, :grade_level, :daily_allowance, :description)
            RETURNING position_id
            """,
            {**data, "division_id": str(data["division_id"]) if data.get("division_id") else None},
        )
        return await self.get(new_id)

    async def update(self, position_id: UUID, fields: dict[str, Any]) -> Any:
        if fields:
            sets = ", ".join(
                f"{k} = CAST(:{k} AS uuid)" if k == "division_id" else f"{k} = :{k}" for k in fields)
            await self.execute(
                f"UPDATE job_position SET {sets}, update_at = now() WHERE position_id = CAST(:id AS uuid)",
                {**{k: (str(v) if k == "division_id" and v else v) for k, v in fields.items()}, "id": str(position_id)},
            )
        return await self.get(position_id)

    async def archive(self, position_id: UUID) -> None:
        await self.execute("UPDATE job_position SET delete_at = now(), update_at = now() "
                           "WHERE position_id = CAST(:id AS uuid)", {"id": str(position_id)})
