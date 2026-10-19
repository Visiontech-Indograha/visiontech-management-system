"""
app/crud/crud_hse.py
Laporan harian dan checklist tugas pekerjaan Master Schema V2 (tabel work_plan_daily & work_plan_item).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_REPORT_COLUMNS = "daily_plan_id AS id, weekly_plan_id, work_date, status, notes AS body, notes AS obstacle"


class HseRepository(BaseRepository):
    """Repositori insiden K3 (HSE) dan toolbox meeting."""
    """Kueri Master Schema V2 untuk laporan harian dan item pekerjaan."""

    async def employee_of_user(self, user_id: UUID | str) -> Any:
        """employee_id milik akun, atau None."""
        row = await self.fetchone(
            "SELECT employee_id FROM users WHERE user_id = CAST(:uid AS uuid) AND delete_at IS NULL",
            {"uid": str(user_id)},
        )
        return row.employee_id if row else None

    async def incidents_of_plan(self, plan_id: UUID | str, org_id: UUID | str) -> list[Any]:
        """Daftar insiden (fallback kosong bila fitur insiden belum diaktifkan)."""
        return []

    async def insert_incident(
        self,
        org_id: UUID | str,
        plan_id: UUID | str,
        employee_id: Any,
        occurred_on: Any,
        category: str,
        severity: str,
        description: str,
    ) -> Any:
        """Insiden baru stub."""
        return None

    async def add_incident_evidence(self, incident_id: UUID | str, file_ids: list[str]) -> None:
        """Lampirkan berkas bukti ke insiden stub."""

    async def resolve_incident(
        self, incident_id: UUID | str, org_id: UUID | str, employee_id: Any, note: str | None
    ) -> Any:
        """Tandai insiden selesai stub."""
        return None

    async def upsert_daily_report(self, day_id: UUID | str, body: str | None, obstacle: str | None) -> Any:
        """Simpan catatan draf laporan harian."""
        note_text = (body or "") + (f"\nKendala: {obstacle}" if obstacle else "")
        return await self.fetchone(
            f"""
            UPDATE work_plan_daily
            SET notes = :note, update_at = NOW()
            WHERE daily_plan_id = CAST(:day AS uuid) AND delete_at IS NULL
            RETURNING {_REPORT_COLUMNS}
            """,
            {"day": str(day_id), "note": note_text},
        )

    async def replace_report_evidence(self, report_id: UUID | str, items: list[tuple[str, str | None, str]]) -> None:
        """Simpan foto bukti ke item laporan harian."""
        photo_urls = [i[0] for i in items]
        await self.execute(
            """
            UPDATE work_plan_item
            SET photo_urls = to_jsonb(CAST(:photos AS text[])), update_at = NOW()
            WHERE daily_plan_id = CAST(:day AS uuid) AND delete_at IS NULL
            """,
            {"day": str(report_id), "photos": photo_urls},
        )

    async def submit_daily_report(self, day_id: UUID | str, employee_id: Any) -> Any:
        """Ajukan laporan harian."""
        return await self.fetchone(
            f"""
            UPDATE work_plan_daily
            SET status = 'SUBMITTED', update_at = NOW()
            WHERE daily_plan_id = CAST(:day AS uuid) AND delete_at IS NULL
            RETURNING {_REPORT_COLUMNS}
            """,
            {"day": str(day_id)},
        )

    async def review_daily_report(self, day_id: UUID | str, status: str, note: str | None, user_id: UUID | str) -> Any:
        """Setujui / kembalikan laporan harian."""
        new_status = "APPROVED" if "APPROV" in status.upper() else "CHANGES_REQUESTED"
        return await self.fetchone(
            f"""
            UPDATE work_plan_daily
            SET status = :status,
                notes = COALESCE(notes, '') || CASE WHEN :note IS NOT NULL THEN E'\\nReview: ' || :note ELSE '' END,
                update_at = NOW()
            WHERE daily_plan_id = CAST(:day AS uuid) AND delete_at IS NULL
            RETURNING {_REPORT_COLUMNS}
            """,
            {"status": new_status, "note": note, "day": str(day_id)},
        )

    async def daily_report_body(self, day_id: UUID | str) -> str | None:
        """Isi uraian catatan laporan harian."""
        value = await self.scalar(
            "SELECT notes FROM work_plan_daily WHERE daily_plan_id = CAST(:day AS uuid) AND delete_at IS NULL",
            {"day": str(day_id)},
        )
        return None if value is None else str(value)

    async def daily_report_status(self, day_id: UUID | str) -> Any:
        """Status laporan harian hari itu, atau None bila belum ada."""
        row = await self.fetchone(
            "SELECT status FROM work_plan_daily WHERE daily_plan_id = CAST(:day AS uuid) AND delete_at IS NULL",
            {"day": str(day_id)},
        )
        return row.status if row else None

    async def toggle_task(self, task_id: UUID | str, day_id: UUID | str, user_id: UUID | str) -> Any:
        """Balik centang tugas hari itu (tabel work_plan_item)."""
        return await self.fetchone(
            """
            UPDATE work_plan_item
            SET status = CASE WHEN status = 'COMPLETED' THEN 'PENDING' ELSE 'COMPLETED' END,
                actual_end = CASE WHEN status = 'COMPLETED' THEN NULL ELSE NOW() END,
                update_at = NOW()
            WHERE item_id = CAST(:task AS uuid) AND daily_plan_id = CAST(:day AS uuid) AND delete_at IS NULL
            RETURNING item_id AS id, (status = 'COMPLETED') AS is_done
            """,
            {"task": str(task_id), "day": str(day_id)},
        )


# Alias backward compatibility
CRUDHse = HseRepository
