"""
app/crud/crud_plan_revision.py
Riwayat revisi rencana kerja mingguan Master Schema V2 (tabel app_activity_logs, work_plan_weekly, employee).
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.core.enums import DocumentStatus

from .base import CRUDBase


class CRUDPlanRevision(CRUDBase):
    """Akses data riwayat revisi rencana kerja Master Schema V2."""

    async def insert_revision(
        self,
        org_id: UUID | str,
        plan_id: UUID | str,
        revision: int,
        revised_by: str,
        reason: str,
        diff: list[dict[str, Any]],
        resolved_change_id: UUID | str | None,
    ) -> None:
        """Menambah satu baris riwayat revisi ke app_activity_logs."""
        await self.execute(
            """
            INSERT INTO app_activity_logs (user_id, action, target_table, target_id, details)
            VALUES (
                COALESCE((SELECT user_id FROM users WHERE employee_id = CAST(:by AS uuid) LIMIT 1),
                         (SELECT user_id FROM users LIMIT 1)),
                'REVISION',
                'work_plan_weekly',
                CAST(:plan AS uuid),
                jsonb_build_object('revision', :rev, 'reason', :reason, 'diff', CAST(:diff AS jsonb))
            )
            """,
            {
                "plan": str(plan_id),
                "by": str(revised_by),
                "rev": revision,
                "reason": reason,
                "diff": json.dumps(diff, default=str, ensure_ascii=False),
            },
        )

    async def list_revisions(self, plan_id: UUID | str) -> list[Any]:
        """Riwayat revisi satu rencana kerja mingguan, terbaru dulu."""
        return list(
            await self.fetchall(
                """
            SELECT l.log_id AS id,
                   COALESCE((l.details->>'revision')::int, 1) AS revision,
                   e.full_name AS revised_by_name,
                   COALESCE(l.details->>'reason', 'Revisi Rencana Kerja') AS reason,
                   COALESCE(l.details->'diff', '[]'::jsonb) AS diff,
                   l.create_at AS created_at
            FROM app_activity_logs l
            JOIN users u ON u.user_id = l.user_id
            JOIN employee e ON e.employee_id = u.employee_id
            WHERE l.target_table = 'work_plan_weekly'
              AND l.target_id = CAST(:plan AS uuid)
              AND l.action = 'REVISION'
            ORDER BY l.create_at DESC
            """,
                {"plan": str(plan_id)},
            )
        )

    async def supersede_awaiting(self, plan_id: UUID | str) -> None:
        pass

    async def issue_revision_document(
        self,
        plan_id: UUID | str,
        version: int,
        snapshot: dict[str, Any],
        issued_by: str,
        reason: str,
        status: DocumentStatus,
    ) -> None:
        await self.execute(
            """
            UPDATE work_plan_weekly
            SET notes = COALESCE(notes, '') || E'\\n[Rev-' || :ver || ']: ' || :reason,
                update_at = NOW()
            WHERE weekly_plan_id = CAST(:plan AS uuid)
            """,
            {"plan": str(plan_id), "ver": version, "reason": reason},
        )

    async def clear_appeal(self, plan_id: UUID | str) -> None:
        """Pengajuan revisi/banding dianggap selesai."""
        await self.execute(
            """
            UPDATE work_plan_weekly
            SET rollover_approval = 'NONE', update_at = NOW()
            WHERE weekly_plan_id = CAST(:plan AS uuid)
            """,
            {"plan": str(plan_id)},
        )

    async def employee_name(self, employee_id: UUID | str) -> str | None:
        """Nama lengkap karyawan."""
        name: str | None = await self.scalar(
            "SELECT full_name FROM employee WHERE employee_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(employee_id)},
        )
        return name
