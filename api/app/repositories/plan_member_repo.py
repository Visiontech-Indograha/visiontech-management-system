"""
app/repositories/plan_member_repo.py
Susunan tim pekerjaan (`work_plan_member`). Anggota aktif = `valid_period` terbuka
(sama dengan `vms.is_plan_member`); adendum personel kelak menutup baris, bukan menghapus.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from typing import Any
from uuid import UUID

from app.core.enums import PlanStatus

from .base_repo import BaseRepo


class PlanMemberRepo(BaseRepo):

    async def lock_plan(self, plan_id: UUID | str, org_id: UUID | str) -> Any:
        """SK milik organisasi ini, dikunci untuk diubah. None bila tidak ada / milik organisasi lain."""
        return await self.fetchone(
            """
            SELECT id, status, row_version, pm_employee_id, lower(period) AS period_start
            FROM vms.work_plan
            WHERE id = :id AND organization_id = :org AND deleted_at IS NULL
            FOR UPDATE
            """,
            {"id": plan_id, "org": org_id},
        )

    async def active_team(self, plan_id: UUID | str) -> list[Any]:
        """Tim aktif SK (valid_period terbuka): ketua dulu, lalu anggota menurut nama."""
        return list(await self.fetchall(
            """
            SELECT CAST(m.employee_id AS text) AS employee_id, CAST(m.role_in_plan AS text) AS role_in_plan,
                   e.full_name, e.position, lower(m.valid_period) AS valid_from
            FROM vms.work_plan_member m JOIN vms.employee e ON e.id = m.employee_id
            WHERE m.work_plan_id = :plan AND upper_inf(m.valid_period)
            ORDER BY (m.role_in_plan = 'LEADER') DESC, e.full_name
            """,
            {"plan": plan_id},
        ))

    async def active_employees(self, employee_ids: Iterable[UUID | str], org_id: UUID | str) -> set[str]:
        ids = [str(e) for e in employee_ids]
        rows = await self.fetchall(
            """
            SELECT id::text FROM vms.employee
            WHERE id = ANY(CAST(:ids AS uuid[])) AND organization_id = :org AND is_active AND deleted_at IS NULL
            """,
            {"ids": ids, "org": org_id},
        )
        return {r[0] for r in rows}

    async def schedule_conflicts(self, employee_ids: Iterable[UUID | str], plan_id: UUID | str) -> Sequence[Any]:
        """Pekerjaan terbit lain yang periodenya beririsan (vms.personnel_conflict)."""
        return await self.fetchall(
            """
            SELECT e.employee_id::text AS employee_id, c.work_plan_id::text AS work_plan_id, c.number, c.title
            FROM unnest(CAST(:ids AS uuid[])) AS e(employee_id)
            CROSS JOIN LATERAL vms.personnel_conflict(
                e.employee_id, (SELECT period FROM vms.work_plan WHERE id = :plan), :plan) AS c
            """,
            {"ids": [str(e) for e in employee_ids], "plan": plan_id},
        )

    async def schedule_conflicts_until(self, employee_ids: Iterable[UUID | str], plan_id: UUID | str,
                                       new_end: date) -> Sequence[Any]:
        """Seperti schedule_conflicts, tetapi untuk periode yang diperpanjang sampai `new_end`
        (domain.js checkSchedule(plan, newEnd) saat menyetujui perpanjangan)."""
        return await self.fetchall(
            """
            SELECT e.employee_id::text AS employee_id, c.work_plan_id::text AS work_plan_id, c.number, c.title
            FROM unnest(CAST(:ids AS uuid[])) AS e(employee_id)
            CROSS JOIN LATERAL vms.personnel_conflict(
                e.employee_id,
                (SELECT daterange(lower(period), CAST(:new_end AS date) + 1, '[)') FROM vms.work_plan WHERE id = :plan),
                :plan) AS c
            """,
            {"ids": [str(e) for e in employee_ids], "plan": plan_id, "new_end": new_end},
        )

    async def replace_team(
        self, plan_id: UUID | str, start: date, leader_id: UUID | str | None, member_ids: Sequence[UUID | str]
    ) -> None:
        """Ganti seluruh susunan tim SK draft (belum ada dokumen terbit, jadi tidak ada riwayat yang hilang)."""
        await self.execute("DELETE FROM vms.work_plan_member WHERE work_plan_id = :plan", {"plan": plan_id})
        rows = ([(leader_id, "LEADER")] if leader_id else []) + [(m, "MEMBER") for m in member_ids]
        for employee_id, role in rows:
            await self.execute(
                """
                INSERT INTO vms.work_plan_member (work_plan_id, employee_id, role_in_plan, valid_period)
                VALUES (:plan, :emp, CAST(:role AS vms.role_code), daterange(CAST(:start AS date), NULL, '[)'))
                """,
                {"plan": plan_id, "emp": employee_id, "role": role, "start": start},
            )

    async def set_leader(self, plan_id: UUID | str, leader_id: UUID | str | None) -> int:
        """Setel ketua di SK dan naikkan row_version. Kembalikan row_version baru."""
        return int(await self.scalar(
            """
            UPDATE vms.work_plan SET leader_employee_id = :leader, row_version = row_version + 1
            WHERE id = :plan AND status = :draft
            RETURNING row_version
            """,
            {"leader": leader_id, "plan": plan_id, "draft": PlanStatus.DRAFT},
        ))
