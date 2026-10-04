"""
app/crud/crud_member_report.py
Laporan harian berjenjang (alur SK v2 PR2, flowchart SK2-E): laporan anggota untuk ketua, dan data dokumen
laporan harian/mingguan yang sudah disetujui PM.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDMemberReport(CRUDBase):

    async def employee_of(self, user_id: UUID | str) -> str | None:
        value = await self.scalar("SELECT CAST(employee_id AS text) FROM vms.app_user WHERE id = :uid", {"uid": user_id})
        return str(value) if value else None

    async def list_for_day(self, day_id: UUID | str) -> list[Any]:
        """Laporan anggota satu hari (yang sudah dikirim maupun draf) beserta nama & jabatan."""
        return list(await self.fetchall(
            """
            SELECT r.id, CAST(r.employee_id AS text) AS employee_id, e.full_name, e.position, r.status, r.body,
                   r.obstacle, r.sent_at,
                   COALESCE(ARRAY(SELECT CAST(ev.file_id AS text) FROM vms.member_report_evidence ev
                                  WHERE ev.member_report_id = r.id ORDER BY ev.file_id), '{}') AS evidence_file_ids
            FROM vms.member_daily_report r JOIN vms.employee e ON e.id = r.employee_id
            WHERE r.work_plan_day_id = :day
            ORDER BY r.sent_at NULLS LAST, e.full_name
            """,
            {"day": day_id},
        ))

    async def mine(self, day_id: UUID | str, employee_id: str) -> Any:
        return await self.fetchone(
            """
            SELECT r.id, CAST(r.employee_id AS text) AS employee_id, e.full_name, e.position, r.status, r.body,
                   r.obstacle, r.sent_at,
                   COALESCE(ARRAY(SELECT CAST(ev.file_id AS text) FROM vms.member_report_evidence ev
                                  WHERE ev.member_report_id = r.id ORDER BY ev.file_id), '{}') AS evidence_file_ids
            FROM vms.member_daily_report r JOIN vms.employee e ON e.id = r.employee_id
            WHERE r.work_plan_day_id = :day AND r.employee_id = CAST(:emp AS uuid)
            """,
            {"day": day_id, "emp": employee_id},
        )

    async def save(self, day_id: UUID | str, employee_id: str, body: str, obstacle: str) -> Any:
        """Simpan draf; laporan yang sudah dikirim tidak berubah (→ None)."""
        return await self.fetchone(
            """
            INSERT INTO vms.member_daily_report (work_plan_day_id, employee_id, body, obstacle)
            VALUES (:day, CAST(:emp AS uuid), :body, :obstacle)
            ON CONFLICT (work_plan_day_id, employee_id) DO UPDATE
               SET body = EXCLUDED.body, obstacle = EXCLUDED.obstacle, updated_at = now()
             WHERE vms.member_daily_report.status = 'DRAFT'
            RETURNING id
            """,
            {"day": day_id, "emp": employee_id, "body": body, "obstacle": obstacle},
        )

    async def replace_evidence(self, report_id: UUID | str, file_ids: Iterable[UUID]) -> None:
        await self.execute("DELETE FROM vms.member_report_evidence WHERE member_report_id = :rid", {"rid": report_id})
        unique_fids = list(dict.fromkeys(file_ids))
        if unique_fids:
            await self.execute(
                """
                INSERT INTO vms.member_report_evidence (member_report_id, file_id)
                SELECT :rid, unnest(CAST(:fids AS uuid[]))
                """,
                {"rid": report_id, "fids": [str(f) for f in unique_fids]}
            )

    async def send(self, day_id: UUID | str, employee_id: str) -> Any:
        return await self.fetchone(
            """
            UPDATE vms.member_daily_report SET status = 'SENT', sent_at = now(), updated_at = now()
             WHERE work_plan_day_id = :day AND employee_id = CAST(:emp AS uuid) AND status = 'DRAFT'
               AND length(btrim(body)) >= 10
            RETURNING id
            """,
            {"day": day_id, "emp": employee_id},
        )

    async def day_info(self, day_id: UUID | str) -> Any:
        return await self.fetchone(
            "SELECT d.work_date, d.title, CAST(d.work_plan_id AS text) AS plan_id FROM vms.work_plan_day d WHERE d.id = :day",
            {"day": day_id})

    # ── Dokumen laporan (A4) ──────────────────────────────────────────────────────────────────
    async def plan_header(self, plan_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT wp.number, wp.title, wp.location_text, wp.category, bu.name AS unit_name,
                   lower(wp.period) AS period_start, upper(wp.period) - 1 AS period_end,
                   pm.full_name AS pm_name, ld.full_name AS leader_name
            FROM vms.work_plan wp
            LEFT JOIN vms.business_unit bu ON bu.id = wp.unit_id
            LEFT JOIN vms.employee pm ON pm.id = wp.pm_employee_id
            LEFT JOIN vms.employee ld ON ld.id = wp.leader_employee_id
            WHERE wp.id = :plan
            """,
            {"plan": plan_id})

    async def daily_report_doc(self, day_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT d.work_date, d.title AS day_title, CAST(r.status AS text) AS status, r.body, r.obstacle,
                   r.resubmitted, r.submitted_at, r.reviewed_at, r.review_note,
                   se.full_name AS submitted_by_name, re.full_name AS reviewed_by_name,
                   COALESCE(ARRAY(SELECT f.file_name FROM vms.report_evidence ev
                                  JOIN vms.file_object f ON f.id = ev.file_id
                                  WHERE ev.daily_report_id = r.id ORDER BY f.file_name), '{}') AS evidence,
                   COALESCE(ARRAY(SELECT t.title FROM vms.work_plan_task t WHERE t.work_plan_day_id = d.id
                                  ORDER BY t.sort_order), '{}') AS tasks
            FROM vms.work_plan_day d
            JOIN vms.daily_report r ON r.work_plan_day_id = d.id
            LEFT JOIN vms.employee se ON se.id = r.submitted_by
            LEFT JOIN vms.employee re ON re.id = r.reviewed_by
            WHERE d.id = :day
            """,
            {"day": day_id})

    async def weekly_report_doc(self, plan_id: UUID | str, name: str) -> Any:
        return await self.fetchone(
            """
            SELECT wr.name, lower(wr.covered_period) AS starts_on, upper(wr.covered_period) - 1 AS ends_on,
                   CAST(wr.status AS text) AS status, wr.body, wr.obstacle, wr.resubmitted, wr.review_note,
                   se.full_name AS submitted_by_name, re.full_name AS reviewed_by_name
            FROM vms.weekly_report wr
            LEFT JOIN vms.employee se ON se.id = wr.submitted_by
            LEFT JOIN vms.employee re ON re.id = wr.reviewed_by
            WHERE wr.work_plan_id = :plan AND wr.name = :name
            """,
            {"plan": plan_id, "name": name})
