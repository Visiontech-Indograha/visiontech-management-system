"""
app/shared/access/daily_access_repository.py
Kedudukan pengguna pada satu jadwal harian (Master Schema V2, daily-first).

Relasi: work_plan_daily N─1 division (om_id, pm_id), work_plan_daily N─1 team (leader_employee_id),
team 1─N member. Kewenangan dibaca dari relasi ini setiap permintaan, bukan dari jabatan saja.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository


class DailyAccessRepository(BaseRepository):
    """Query kedudukan (PM/OM divisi, ketua, anggota) atas work_plan_daily."""

    async def standing(self, daily_plan_id: UUID | str, employee_id: UUID | str | None) -> Any:
        return await self.fetchone(
            """
            SELECT wpd.daily_plan_id, wpd.status, wpd.kind, wpd.work_date, wpd.division_id, wpd.team_id,
                   d.pm_id, d.om_id, t.leader_employee_id,
                   (CAST(:emp AS uuid) IS NOT NULL AND CAST(:emp AS uuid) IN (d.pm_id, d.om_id)) AS manages,
                   (t.leader_employee_id = CAST(:emp AS uuid)) AS is_leader,
                   EXISTS (SELECT 1 FROM member m WHERE m.team_id = wpd.team_id
                           AND m.employee_id = CAST(:emp AS uuid) AND m.is_active AND m.delete_at IS NULL) AS is_member
            FROM work_plan_daily wpd
            JOIN division d ON d.division_id = wpd.division_id
            JOIN team t ON t.team_id = wpd.team_id
            WHERE wpd.daily_plan_id = CAST(:id AS uuid) AND wpd.delete_at IS NULL
            """,
            {"id": str(daily_plan_id), "emp": str(employee_id) if employee_id else None},
        )

    async def division_managers(self, division_id: UUID | str) -> Any:
        """PM & OM divisi aktif — dasar kewenangan membuat jadwal untuk divisi itu."""
        return await self.fetchone(
            "SELECT division_id, pm_id, om_id FROM division "
            "WHERE division_id = CAST(:id AS uuid) AND delete_at IS NULL AND status",
            {"id": str(division_id)},
        )
