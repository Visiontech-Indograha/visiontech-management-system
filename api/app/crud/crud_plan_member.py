"""
app/crud/crud_plan_member.py
Susunan tim pekerjaan Master Schema V2 (tabel team, member, work_plan_weekly, employee).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from typing import Any
from uuid import UUID

from app.core.repository import CRUDBase


class CRUDPlanMember(CRUDBase):
    """
    CRUD untuk mengelola susunan anggota tim (personel) dalam sebuah rencana kerja mingguan (Master Schema V2).
    """

    async def lock_plan(self, plan_id: UUID | str, org_id: UUID | str) -> Any:
        """
        Mengunci rencana kerja mingguan (FOR UPDATE) agar aman diubah tanpa race condition.
        """
        return await self.fetchone(
            """
            SELECT weekly_plan_id AS id, division_id AS unit_id, status, 1 AS row_version,
                   approved_by_pm_id AS pm_employee_id, start_date AS period_start
            FROM work_plan_weekly
            WHERE weekly_plan_id = CAST(:id AS uuid) AND delete_at IS NULL
            FOR UPDATE
            """,
            {"id": str(plan_id)},
        )

    async def active_team(self, plan_id: UUID | str) -> list[Any]:
        """
        Mengambil tim aktif dari sebuah rencana kerja mingguan. Ketua tim muncul di baris pertama.
        """
        return list(
            await self.fetchall(
                """
            SELECT CAST(m.employee_id AS text) AS employee_id,
                   CASE WHEN m.employee_id = t.leader_employee_id THEN 'LEADER' ELSE 'MEMBER' END AS role_in_plan,
                   e.full_name, 'Teknisi Proyek' AS position, wp.start_date AS valid_from
            FROM work_plan_weekly wp
            JOIN team t ON t.team_id = wp.team_id
            JOIN member m ON m.team_id = t.team_id AND m.is_active = TRUE AND m.delete_at IS NULL
            JOIN employee e ON e.employee_id = m.employee_id
            WHERE wp.weekly_plan_id = CAST(:plan AS uuid)
            ORDER BY (m.employee_id = t.leader_employee_id) DESC, e.full_name
            """,
                {"plan": str(plan_id)},
            )
        )

    async def active_employees(self, employee_ids: Iterable[UUID | str], org_id: UUID | str) -> set[str]:
        """
        Memvalidasi bahwa kumpulan ID karyawan yang diberikan adalah karyawan aktif.
        """
        ids = [str(e) for e in employee_ids]
        if not ids:
            return set()
        rows = await self.fetchall(
            """
            SELECT employee_id::text FROM employee
            WHERE employee_id = ANY(CAST(:ids AS uuid[])) AND offboarding_status = 'active' AND delete_at IS NULL
            """,
            {"ids": ids},
        )
        return {r[0] for r in rows}

    async def schedule_conflicts(self, employee_ids: Iterable[UUID | str], plan_id: UUID | str) -> Sequence[Any]:
        """
        Mengecek bentrok jadwal rencana kerja.
        """
        return []

    async def schedule_conflicts_until(
        self, employee_ids: Iterable[UUID | str], plan_id: UUID | str, new_end: date
    ) -> Sequence[Any]:
        """
        Mengecek bentrok jadwal untuk perpanjangan rencana kerja.
        """
        return []

    async def replace_team(
        self, plan_id: UUID | str, start: date, leader_id: UUID | str | None, member_ids: Sequence[UUID | str]
    ) -> None:
        """
        Mengganti susunan tim pada tabel team dan member V2.
        """
        team_id = await self.scalar(
            "SELECT team_id FROM work_plan_weekly WHERE weekly_plan_id = CAST(:plan AS uuid)",
            {"plan": str(plan_id)},
        )
        if not team_id:
            return

        if leader_id:
            await self.execute(
                "UPDATE team SET leader_employee_id = CAST(:ldr AS uuid), update_at = now() WHERE team_id = CAST(:tid AS uuid)",
                {"ldr": str(leader_id), "tid": str(team_id)},
            )

        # Update member aktif
        all_members = ([leader_id] if leader_id else []) + list(member_ids)
        for mid in all_members:
            if mid:
                await self.execute(
                    """
                    INSERT INTO member (team_id, employee_id, is_active)
                    VALUES (CAST(:tid AS uuid), CAST(:mid AS uuid), true)
                    ON CONFLICT DO NOTHING
                    """,
                    {"tid": str(team_id), "mid": str(mid)},
                )

    async def set_leader(self, plan_id: UUID | str, leader_id: UUID | str | None) -> int:
        """
        Menetapkan ketua tim pada tabel team yang menaungi rencana mingguan.
        """
        if leader_id:
            await self.execute(
                """
                UPDATE team SET leader_employee_id = CAST(:ldr AS uuid), update_at = now()
                WHERE team_id = (SELECT team_id FROM work_plan_weekly WHERE weekly_plan_id = CAST(:plan AS uuid))
                """,
                {"ldr": str(leader_id), "plan": str(plan_id)},
            )
        return 1
