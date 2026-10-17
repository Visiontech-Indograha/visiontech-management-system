"""
app/crud/crud_plan_change.py
Usulan perubahan rencana kerja mingguan (perpanjangan waktu & personel) Master Schema V2.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from app.core.enums import ChangeStatus, ChangeType, DocumentKind, DocumentStatus

from .base import CRUDBase

_DAY_TITLES = ("Persiapan & survei lokasi", "Instalasi & konfigurasi", "Pengujian & serah terima")
_DAY_TASKS = ("Briefing keselamatan dan pemeriksaan area", "Pelaksanaan pekerjaan sesuai rencana")


class CRUDPlanChange(CRUDBase):
    """
    Kelas CRUD untuk memproses usulan perubahan (adendum) pada rencana kerja mingguan Master Schema V2.
    """

    async def employee_of(self, user_id: UUID | str) -> Any:
        """Mengambil ID Karyawan (employee_id) dari seorang pengguna."""
        return await self.scalar(
            "SELECT CAST(employee_id AS text) FROM users WHERE user_id = CAST(:uid AS uuid) AND delete_at IS NULL",
            {"uid": str(user_id)},
        )

    async def get_change(self, change_id: UUID | str) -> Any:
        """Mengambil rincian data usulan perubahan."""
        return await self.fetchone(
            """
            SELECT l.log_id AS id,
                   CAST(l.target_id AS text) AS work_plan_id,
                   'EXTENSION' AS change_type,
                   CAST(wp.rollover_approval AS text) AS status,
                   COALESCE(l.details->>'reason', wp.notes) AS reason,
                   l.details->>'decision_reason' AS decision_reason
            FROM app_activity_logs l
            JOIN work_plan_weekly wp ON wp.weekly_plan_id = l.target_id
            WHERE l.log_id = CAST(:id AS uuid)
            """,
            {"id": str(change_id)},
        )

    async def open_change(self, plan_id: UUID | str) -> Any:
        """Memeriksa apakah ada usulan perubahan yang masih terbuka."""
        return await self.scalar(
            """
            SELECT weekly_plan_id FROM work_plan_weekly
            WHERE weekly_plan_id = CAST(:plan AS uuid) AND rollover_approval = 'WAITING_PM'
            """,
            {"plan": str(plan_id)},
        )

    async def lock_change(self, change_id: UUID | str, org_id: UUID | str) -> Any:
        """Usulan + rencana mingguan (dikunci)."""
        return await self.fetchone(
            """
            SELECT wp.weekly_plan_id AS id, wp.weekly_plan_id AS work_plan_id,
                   'EXTENSION' AS change_type, wp.rollover_approval AS status,
                   wp.notes AS reason, 1 AS base_revision, 2 AS proposed_revision,
                   wp.end_date AS new_period_end, CAST(t.leader_employee_id AS text) AS proposed_leader_id,
                   '[]'::jsonb AS proposed_members, NULL AS document_id, 1 AS plan_revision,
                   wp.status AS plan_status, wp.start_date AS period_start, wp.end_date AS period_end
            FROM work_plan_weekly wp
            JOIN team t ON t.team_id = wp.team_id
            WHERE wp.weekly_plan_id = CAST(:id AS uuid) AND wp.delete_at IS NULL
            FOR UPDATE OF wp
            """,
            {"id": str(change_id)},
        )

    async def next_document_version(self, plan_id: UUID | str) -> int:
        return 2

    async def insert_change(
        self,
        *,
        plan_id: UUID | str,
        change_type: ChangeType,
        status: ChangeStatus,
        reason: str,
        base_revision: int,
        proposed_revision: int,
        requested_by: str,
        old_end: date | None = None,
        new_end: date | None = None,
        leader_id: str | None = None,
        member_ids: list[str] | None = None,
    ) -> Any:
        """Memasukkan usulan perubahan baru ke app_activity_logs & update rollover_approval."""
        await self.execute(
            """
            UPDATE work_plan_weekly
            SET rollover_approval = 'WAITING_PM', update_at = NOW()
            WHERE weekly_plan_id = CAST(:plan AS uuid)
            """,
            {"plan": str(plan_id)},
        )
        row = await self.fetchone(
            """
            INSERT INTO app_activity_logs (user_id, action, target_table, target_id, details)
            VALUES (
                COALESCE((SELECT user_id FROM users WHERE employee_id = CAST(:by AS uuid) LIMIT 1),
                         (SELECT user_id FROM users LIMIT 1)),
                'CHANGE_REQUEST',
                'work_plan_weekly',
                CAST(:plan AS uuid),
                jsonb_build_object(
                    'type', CAST(:type AS text),
                    'status', CAST(:status AS text),
                    'reason', :reason,
                    'old_end', :old_end,
                    'new_end', :new_end,
                    'leader_id', :leader,
                    'members', CAST(:members AS text[])
                )
            )
            RETURNING log_id AS id
            """,
            {
                "plan": str(plan_id),
                "by": str(requested_by),
                "type": str(change_type),
                "status": str(status),
                "reason": reason,
                "old_end": str(old_end) if old_end else None,
                "new_end": str(new_end) if new_end else None,
                "leader": str(leader_id) if leader_id else None,
                "members": [str(m) for m in (member_ids or [])],
            },
        )
        return row.id

    async def issue_addendum(
        self,
        change_id: UUID | str,
        plan_id: UUID | str,
        kind: DocumentKind,
        version: int,
        snapshot: dict[str, Any],
        issued_by: str,
        reason: str,
    ) -> None:
        await self.execute(
            """
            UPDATE work_plan_weekly
            SET notes = COALESCE(notes, '') || E'\\n[Adendum]: ' || :reason, update_at = NOW()
            WHERE weekly_plan_id = CAST(:plan AS uuid)
            """,
            {"plan": str(plan_id), "reason": reason},
        )

    async def pending_amendment_ids(self, plan_id: UUID | str) -> list[str]:
        rows = await self.fetchall(
            """
            SELECT CAST(weekly_plan_id AS text) AS id FROM work_plan_weekly
            WHERE weekly_plan_id = CAST(:plan AS uuid) AND rollover_approval = 'WAITING_PM'
            """,
            {"plan": str(plan_id)},
        )
        return [r.id for r in rows]

    async def set_change(
        self,
        change_id: UUID | str,
        status: ChangeStatus,
        decided_by: str | None = None,
        decision_reason: str | None = None,
    ) -> None:
        approval_val = "APPROVED_BY_PM" if "APPROV" in str(status).upper() else "REJECTED_BY_PM"
        await self.execute(
            """
            UPDATE work_plan_weekly
            SET rollover_approval = CAST(:app AS rollover_approval_enum), update_at = NOW()
            WHERE weekly_plan_id = CAST(:id AS uuid)
            """,
            {"id": str(change_id), "app": approval_val},
        )

    async def set_document(
        self, document_id: UUID | str | None, status: DocumentStatus, accepted_by: str | None = None
    ) -> None:
        pass

    async def apply_extension(self, plan_id: UUID | str, old_end: date, new_end: date, revision: int) -> None:
        """Perpanjang periode rencana kerja mingguan dan tambahkan hari kerja baru."""
        await self.execute(
            """
            UPDATE work_plan_weekly
            SET end_date = CAST(:new_end AS date), rollover_approval = 'APPROVED_BY_PM', update_at = NOW()
            WHERE weekly_plan_id = CAST(:plan AS uuid)
            """,
            {"plan": str(plan_id), "new_end": new_end},
        )
        day = old_end + timedelta(days=1)
        while day <= new_end:
            day_id = await self.scalar(
                """
                INSERT INTO work_plan_daily (weekly_plan_id, work_date, notes)
                VALUES (CAST(:plan AS uuid), :day, :title)
                RETURNING daily_plan_id
                """,
                {"plan": str(plan_id), "day": day, "title": "Hari Perpanjangan " + str(day)},
            )
            if day_id:
                wt_id = await self.scalar("SELECT work_type_id FROM work_type WHERE delete_at IS NULL LIMIT 1")
                if wt_id:
                    await self.execute(
                        """
                        INSERT INTO work_plan_item (daily_plan_id, work_type_id, description, status)
                        VALUES (CAST(:day AS uuid), CAST(:wt AS uuid), 'Pekerjaan lanjutan perpanjangan', 'PENDING')
                        """,
                        {"day": str(day_id), "wt": str(wt_id)},
                    )
            day += timedelta(days=1)

    async def apply_personnel(self, plan_id: UUID | str, leader_id: str, member_ids: list[str], revision: int) -> None:
        """Ganti ketua tim dan susunan anggota."""
        team_id = await self.scalar(
            "SELECT team_id FROM work_plan_weekly WHERE weekly_plan_id = CAST(:plan AS uuid)",
            {"plan": str(plan_id)},
        )
        if team_id:
            await self.execute(
                "UPDATE team SET leader_employee_id = CAST(:ldr AS uuid), update_at = NOW() WHERE team_id = CAST(:team AS uuid)",
                {"ldr": str(leader_id), "team": str(team_id)},
            )
            # Nonaktifkan anggota lama yang tidak ada di daftar baru
            await self.execute(
                """
                UPDATE member SET is_active = FALSE, update_at = NOW()
                WHERE team_id = CAST(:team AS uuid) AND employee_id <> ALL(CAST(:emps AS uuid[]))
                """,
                {"team": str(team_id), "emps": [str(m) for m in ([leader_id, *member_ids])]},
            )
            # Aktifkan atau sisipkan anggota baru
            for emp in [leader_id, *member_ids]:
                await self.execute(
                    """
                    INSERT INTO member (team_id, employee_id, is_active)
                    VALUES (CAST(:team AS uuid), CAST(:emp AS uuid), TRUE)
                    ON CONFLICT DO NOTHING
                    """,
                    {"team": str(team_id), "emp": str(emp)},
                )
