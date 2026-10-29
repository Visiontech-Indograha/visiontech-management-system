"""
app/modules/work_plans/repositories/daily_correction_repository.py
Query tabel daily_report_correction (koreksi laporan harian). Satu koreksi terbuka per jadwal (indeks unik).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_SELECT = """
    SELECT c.correction_id, c.daily_plan_id, wpd.work_date, wpd.site_name, t.name AS team_name,
           c.requested_by_id, e.full_name AS requested_by_name, c.reason, c.status, c.review_note,
           c.reviewed_at, c.revision_count, c.create_at
    FROM daily_report_correction c
    JOIN work_plan_daily wpd ON wpd.daily_plan_id = c.daily_plan_id
    JOIN team t ON t.team_id = wpd.team_id
    JOIN division d ON d.division_id = wpd.division_id
    JOIN employee e ON e.employee_id = c.requested_by_id
"""


class DailyCorrectionRepository(BaseRepository):
    """Query koreksi laporan harian."""

    async def insert(self, daily_plan_id: UUID | str, requested_by: UUID | str, reason: str) -> UUID:
        correction_id: UUID = await self.scalar(
            "INSERT INTO daily_report_correction (daily_plan_id, requested_by_id, reason) "
            "VALUES (CAST(:p AS uuid), CAST(:e AS uuid), :r) RETURNING correction_id",
            {"p": str(daily_plan_id), "e": str(requested_by), "r": reason},
        )
        return correction_id

    async def get(self, correction_id: UUID | str) -> Any:
        return await self.fetchone(
            _SELECT + " WHERE c.correction_id = CAST(:id AS uuid) AND c.delete_at IS NULL",
            {"id": str(correction_id)},
        )

    async def for_update(self, correction_id: UUID | str) -> Any:
        return await self.fetchone(
            "SELECT correction_id, daily_plan_id, requested_by_id, status, revision_count "
            "FROM daily_report_correction WHERE correction_id = CAST(:id AS uuid) AND delete_at IS NULL FOR UPDATE",
            {"id": str(correction_id)},
        )

    async def of_plan(self, daily_plan_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            _SELECT + " WHERE c.daily_plan_id = CAST(:p AS uuid) AND c.delete_at IS NULL ORDER BY c.create_at DESC",
            {"p": str(daily_plan_id)},
        ))

    async def inbox(self, employee_id: UUID | str | None, status: str | None, *, all_divisions: bool) -> list[Any]:
        """Pengajuan yang relevan: PM/OM melihat divisinya, ketua tim melihat yang dibuatnya; admin semua."""
        return list(await self.fetchall(
            _SELECT + """
            WHERE c.delete_at IS NULL
              AND (CAST(:st AS text) IS NULL OR c.status = CAST(:st AS text))
              AND (CAST(:all AS boolean)
                   OR CAST(:emp AS uuid) IN (d.pm_id, d.om_id)
                   OR t.leader_employee_id = CAST(:emp AS uuid))
            ORDER BY (c.status IN ('REQUESTED', 'IN_REVIEW')) DESC, c.create_at DESC
            """,
            {"st": status, "all": all_divisions, "emp": str(employee_id) if employee_id else None},
        ))

    async def set_status(
        self, correction_id: UUID | str, status: str, *, reviewer: str | None = None, note: str | None = None,
        bump_revision: bool = False,
    ) -> None:
        await self.execute(
            """
            UPDATE daily_report_correction SET
                status = :st,
                reviewed_by_id = COALESCE(CAST(:rev AS uuid), reviewed_by_id),
                reviewed_at = CASE WHEN CAST(:rev AS uuid) IS NULL THEN reviewed_at ELSE now() END,
                review_note = CASE WHEN CAST(:rev AS uuid) IS NULL THEN review_note ELSE CAST(:note AS text) END,
                revision_count = revision_count + CASE WHEN CAST(:bump AS boolean) THEN 1 ELSE 0 END,
                update_at = now()
            WHERE correction_id = CAST(:id AS uuid)
            """,
            {"id": str(correction_id), "st": status, "rev": reviewer, "note": note, "bump": bump_revision},
        )

    async def has_report(self, daily_plan_id: UUID | str) -> bool:
        return bool(await self.scalar(
            "SELECT 1 FROM work_plan_daily_report WHERE daily_plan_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(daily_plan_id)},
        ))

    async def set_plan_status(self, daily_plan_id: UUID | str, status: str) -> None:
        await self.execute(
            "UPDATE work_plan_daily SET status = CAST(:st AS varchar), update_at = now() "
            "WHERE daily_plan_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(daily_plan_id), "st": status},
        )
