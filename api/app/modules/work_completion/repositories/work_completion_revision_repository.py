"""
app/modules/work_completion/repositories/work_completion_revision_repository.py
Akses data revisi pekerjaan dari klien dan keputusan ACC (work_completion_revision).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository
from app.modules.work_completion.repositories.work_completion_core_repository import _row_to_dict


class WorkCompletionRevisionRepository(BaseRepository):
    """Query revisi order klien dan keputusan ACC."""

    async def set_acc_decision(
        self,
        completion_id: UUID | str,
        decision: str,
        decided_by_id: UUID | str | None,
        notes: str | None = None,
        *,
        order_status: str,
        expected_status: str,
    ) -> int:
        """Menyimpan keputusan ACC klien (MENUNGGU_ACC, DITERIMA, DITOLAK_REWORK). Compare-and-set pada
        `expected_status`; kembalian = jumlah baris yang berubah (0 = status sudah diubah pihak lain)."""
        sql = """
            UPDATE work_completion
            SET acc_status = CAST(:decision AS varchar),
                order_status = CAST(:order_status AS varchar),
                acc_decided_at = CASE WHEN CAST(:decision AS varchar) = 'MENUNGGU_ACC' THEN NULL ELSE NOW() END,
                acc_decided_by_id = CASE WHEN CAST(:decision AS varchar) = 'MENUNGGU_ACC'
                                    THEN NULL ELSE CAST(:decided_by AS uuid) END,
                acc_notes = :notes,
                update_at = NOW()
            WHERE completion_id = CAST(:id AS uuid) AND delete_at IS NULL AND order_status = :expected
        """
        result = await self.execute(
            sql,
            {
                "id": str(completion_id),
                "decision": decision,
                "order_status": order_status,
                "expected": expected_status,
                "decided_by": str(decided_by_id) if decided_by_id else None,
                "notes": notes,
            },
        )
        return int(result.rowcount or 0)

    async def reopen_items_for_rework(self, completion_id: UUID | str) -> int:
        """Buka kembali item pengerjaan deliverable jika klien menolak untuk perbaikan (rework)."""
        sql = """
            UPDATE work_plan_item
            SET status = 'TODO',
                source_type = 'REWORK',
                completed_qty = 0,
                progress_percent = 0,
                update_at = NOW()
            WHERE completion_id = CAST(:id AS uuid)
              AND is_main_deliverable = TRUE
              AND delete_at IS NULL
        """
        result = await self.execute(sql, {"id": str(completion_id)})
        return getattr(result, "rowcount", 0)

    async def create_revision(
        self,
        completion_id: UUID | str,
        description: str,
        request_date: Any,
        created_by_id: UUID | str | None,
        survey_task_id: UUID | str | None = None,
    ) -> UUID:
        """Mencatat revisi/tambahan pekerjaan dari klien."""
        sql = """
            INSERT INTO work_completion_revision (
                completion_id, description, request_date, survey_task_id, status, created_by_id
            ) VALUES (
                CAST(:cid AS uuid), :desc, COALESCE(:req_date, CURRENT_DATE),
                CAST(:survey_id AS uuid), 'PENDING', CAST(:creator AS uuid)
            )
            RETURNING revision_id
        """
        res = await self.scalar(
            sql,
            {
                "cid": str(completion_id),
                "desc": description.strip(),
                "req_date": request_date,
                "survey_id": str(survey_task_id) if survey_task_id else None,
                "creator": str(created_by_id) if created_by_id else None,
            },
        )
        return UUID(str(res))

    async def list_revisions(self, completion_id: UUID | str) -> list[dict[str, Any]]:
        """Membaca daftar revisi untuk order klien."""
        sql = """
            SELECT r.revision_id, r.completion_id, r.description, r.request_date, r.survey_task_id,
                   r.status, r.created_by_id, e.full_name AS created_by_name, r.create_at
            FROM work_completion_revision r
            LEFT JOIN employee e ON e.employee_id = r.created_by_id
            WHERE r.completion_id = CAST(:id AS uuid) AND r.delete_at IS NULL
            ORDER BY r.create_at DESC
        """
        rows = await self.fetchall(sql, {"id": str(completion_id)})
        return [_row_to_dict(r) for r in rows]
