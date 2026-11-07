"""
project N─1 client, N─1 office, N─1 division, N─1 employee (pm_id); project 1─N work_plan_daily & work_completion.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.list_params import MAX_ROWS_UNPAGED
from app.core.repository import BaseRepository, escape_like, safe_columns

_SELECT = """
    SELECT p.project_id, p.client_id, c.name AS client_name, p.office_id, o.name AS office_name,
           p.division_id, d.name AS division_name, p.pm_id, e.full_name AS pm_name, p.spk_number, p.project_title,
           p.total_target_qty, p.unit_measure, p.start_date, p.end_date, p.status,
           (SELECT COUNT(*) FROM work_plan_daily w WHERE w.project_id = p.project_id AND w.delete_at IS NULL)::int
               AS daily_plan_count,
           (SELECT COUNT(*) FROM work_completion wc WHERE wc.project_id = p.project_id AND wc.delete_at IS NULL)::int
               AS order_count
    FROM project p
    JOIN client c ON c.client_id = p.client_id
    JOIN office o ON o.office_id = p.office_id
    JOIN division d ON d.division_id = p.division_id
    JOIN employee e ON e.employee_id = p.pm_id
"""
# Lingkup baca: semua (admin/HR) | divisi yang dikelola (PM/OM) | tim lapangan yang punya jadwal di proyek itu.
_SCOPE = """
    AND (CAST(:all AS boolean)
         OR (CAST(:emp AS uuid) IN (d.pm_id, d.om_id, p.pm_id))
         OR EXISTS (SELECT 1 FROM work_plan_daily w JOIN member m ON m.team_id = w.team_id
                    AND m.employee_id = CAST(:emp AS uuid) AND m.is_active AND m.delete_at IS NULL
                    WHERE w.project_id = p.project_id AND w.delete_at IS NULL
                      AND w.status IN ('APPROVED', 'ONGOING', 'COMPLETED')))
"""


class ProjectRepository(BaseRepository):
    async def list(self, *, see_all: bool, employee_id: str | None, division_id: UUID | None,
                   client_id: UUID | None, status: str | None, q: str | None) -> list[Any]:
        return list(await self.fetchall(
            _SELECT + " WHERE p.delete_at IS NULL" + _SCOPE + """
              AND (CAST(:div AS uuid) IS NULL OR p.division_id = CAST(:div AS uuid))
              AND (CAST(:client AS uuid) IS NULL OR p.client_id = CAST(:client AS uuid))
              AND (CAST(:status AS varchar) IS NULL OR p.status = CAST(:status AS varchar))
              AND (CAST(:q AS varchar) IS NULL OR p.project_title ILIKE CAST(:q AS varchar) || '%'
                   OR p.spk_number ILIKE CAST(:q AS varchar) || '%')
            ORDER BY (p.status = 'ONGOING') DESC, p.start_date DESC
            LIMIT :cap
            """,
            {"all": see_all, "emp": employee_id, "div": str(division_id) if division_id else None,
             "client": str(client_id) if client_id else None, "status": status, "q": escape_like(q),
             "cap": MAX_ROWS_UNPAGED},
        ))

    async def get(self, project_id: UUID | str, *, see_all: bool = True, employee_id: str | None = None) -> Any:
        return await self.fetchone(
            _SELECT + " WHERE p.project_id = CAST(:id AS uuid) AND p.delete_at IS NULL" + _SCOPE,
            {"id": str(project_id), "all": see_all, "emp": employee_id},
        )

    async def spk_taken(self, spk: str, exclude: UUID | None = None) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM project WHERE lower(spk_number) = lower(:spk) AND delete_at IS NULL "
            "AND (CAST(:ex AS uuid) IS NULL OR project_id <> CAST(:ex AS uuid)))",
            {"spk": spk, "ex": str(exclude) if exclude else None},
        ))

    async def refs_ok(self, client_id: UUID, office_id: UUID) -> tuple[bool, bool]:
        row = await self.fetchone(
            "SELECT EXISTS (SELECT 1 FROM client WHERE client_id = CAST(:c AS uuid) AND delete_at IS NULL "
            "AND status) AS client, "
            "EXISTS (SELECT 1 FROM office WHERE office_id = CAST(:o AS uuid) AND delete_at IS NULL) AS office",
            {"c": str(client_id), "o": str(office_id)},
        )
        return bool(row.client), bool(row.office)

    async def employee_role(self, employee_id: UUID) -> str | None:
        role: str | None = await self.scalar(
            "SELECT u.system_role::text FROM users u JOIN employee e ON e.employee_id = u.employee_id "
            "WHERE e.employee_id = CAST(:id AS uuid) AND e.delete_at IS NULL AND u.is_active "
            "AND e.offboarding_status = 'active'",
            {"id": str(employee_id)},
        )
        return role

    async def division_pm(self, division_id: UUID) -> Any:
        return await self.scalar("SELECT pm_id FROM division WHERE division_id = CAST(:id AS uuid) "
                                 "AND delete_at IS NULL", {"id": str(division_id)})

    async def insert(self, data: dict[str, Any]) -> Any:
        new_id = await self.scalar(
            """
            INSERT INTO project (client_id, office_id, division_id, pm_id, spk_number, project_title,
                                 total_target_qty, unit_measure, start_date, end_date, status)
            VALUES (CAST(:client_id AS uuid), CAST(:office_id AS uuid), CAST(:division_id AS uuid),
                    CAST(:pm_id AS uuid), :spk_number, :project_title, :total_target_qty, :unit_measure,
                    :start_date, :end_date, :status)
            RETURNING project_id
            """,
            {**data, **{k: str(data[k]) for k in ("client_id", "office_id", "division_id", "pm_id")}},
        )
        return await self.get(new_id)

    async def update(self, project_id: UUID, fields: dict[str, Any]) -> Any:
        uuids = {"client_id", "office_id", "pm_id"}
        if fields:
            sets = ", ".join(f"{k} = CAST(:{k} AS uuid)" if k in uuids else f"{k} = :{k}" for k in safe_columns(fields))
            await self.execute(
                f"UPDATE project SET {sets}, update_at = now() WHERE project_id = CAST(:id AS uuid)",
                {**{k: (str(v) if k in uuids else v) for k, v in fields.items()}, "id": str(project_id)},
            )
        return await self.get(project_id)

    async def archive(self, project_id: UUID) -> None:
        await self.execute("UPDATE project SET delete_at = now(), update_at = now() "
                           "WHERE project_id = CAST(:id AS uuid)", {"id": str(project_id)})
