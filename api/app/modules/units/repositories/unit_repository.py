"""
app/modules/units/repositories/unit_repository.py
Divisi operasional (tabel `division`, Master Schema V2).

Relasi: division N─1 employee (om_id, pm_id); division 1─N employee, team, work_type, work_plan_weekly,
tool, vehicle. Penghapusan = soft delete (`delete_at`).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_SELECT = """
    SELECT
        d.division_id AS id,
        d.division_id,
        'DIV-' || UPPER(SUBSTRING(d.name FROM 1 FOR 3)) AS code,
        d.name,
        d.status,
        d.om_id,
        d.pm_id,
        e_om.full_name AS om_name,
        e_pm.full_name AS pm_name,
        (SELECT count(*)::int FROM team t WHERE t.division_id = d.division_id AND t.delete_at IS NULL) AS team_count
    FROM division d
    LEFT JOIN employee e_om ON e_om.employee_id = d.om_id
    LEFT JOIN employee e_pm ON e_pm.employee_id = d.pm_id
"""


class UnitRepository(BaseRepository):
    """Repositori divisi operasional (tabel `division`)."""

    async def list_for_org(self, org_id: UUID | str) -> list[Any]:
        """Semua divisi aktif."""
        return list(await self.fetchall(f"{_SELECT} WHERE d.delete_at IS NULL ORDER BY d.name"))

    async def get(self, division_id: UUID | str) -> Any:
        return await self.fetchone(
            f"{_SELECT} WHERE d.division_id = CAST(:id AS uuid) AND d.delete_at IS NULL",
            {"id": str(division_id)},
        )

    async def employee_role(self, employee_id: UUID | str) -> str | None:
        """system_role akun milik karyawan aktif (employee 1─1 users); None bila tidak ada/nonaktif."""
        role: str | None = await self.scalar(
            """
            SELECT u.system_role::text
            FROM employee e
            JOIN users u ON u.employee_id = e.employee_id AND u.delete_at IS NULL AND u.is_active
            WHERE e.employee_id = CAST(:emp AS uuid) AND e.delete_at IS NULL
              AND e.offboarding_status = 'active'
            """,
            {"emp": str(employee_id)},
        )
        return role

    async def insert(self, name: str, om_id: UUID | str, pm_id: UUID | str) -> Any:
        row = await self.fetchone(
            """
            INSERT INTO division (name, om_id, pm_id)
            VALUES (:name, CAST(:om AS uuid), CAST(:pm AS uuid))
            RETURNING division_id
            """,
            {"name": name, "om": str(om_id), "pm": str(pm_id)},
        )
        return await self.get(row.division_id)

    async def update(
        self, division_id: UUID | str, *, name: str | None, om_id: UUID | None, pm_id: UUID | None,
        status: bool | None,
    ) -> Any:
        """Ubah sebagian; nilai None = tidak diubah."""
        await self.execute(
            """
            UPDATE division SET
                name = COALESCE(:name, name),
                om_id = COALESCE(CAST(:om AS uuid), om_id),
                pm_id = COALESCE(CAST(:pm AS uuid), pm_id),
                status = COALESCE(CAST(:status AS boolean), status),
                update_at = now()
            WHERE division_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {
                "id": str(division_id),
                "name": name,
                "om": str(om_id) if om_id else None,
                "pm": str(pm_id) if pm_id else None,
                "status": status,
            },
        )
        return await self.get(division_id)

    async def in_use(self, division_id: UUID | str) -> tuple[int, int]:
        """(tim aktif, karyawan aktif) yang masih merujuk divisi ini."""
        row = await self.fetchone(
            """
            SELECT
                (SELECT count(*)::int FROM team WHERE division_id = CAST(:id AS uuid) AND delete_at IS NULL)
                    AS teams,
                (SELECT count(*)::int FROM employee WHERE division_id = CAST(:id AS uuid) AND delete_at IS NULL)
                    AS employees
            """,
            {"id": str(division_id)},
        )
        return (int(row.teams), int(row.employees)) if row else (0, 0)

    async def archive(self, division_id: UUID | str) -> None:
        await self.execute(
            "UPDATE division SET delete_at = now(), update_at = now() "
            "WHERE division_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(division_id)},
        )


CRUDUnit = UnitRepository
