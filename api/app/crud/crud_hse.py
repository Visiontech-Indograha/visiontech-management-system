"""
app/crud/crud_hse.py
Insiden K3 dan laporan harian (beserta bukti & checklist tugas hari itu). Satu-satunya tempat SQL HSE.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase

_INCIDENT_COLUMNS = """id, work_plan_id, reported_by, occurred_on, category, severity, description, status,
                       resolved_by, resolved_at, resolution_note, created_at"""
_EVIDENCE_IDS = """COALESCE(ARRAY(SELECT ie.file_id FROM vms.incident_evidence ie WHERE ie.incident_id = {ref}),
                            '{{}}') AS evidence_file_ids"""
_REPORT_COLUMNS = "id, work_plan_day_id, status, body, obstacle, submitted_by, submitted_at, reviewed_at, resubmitted"


class CRUDHse(CRUDBase):
    """Kueri `incident_report`, `incident_evidence`, `daily_report`, `report_evidence`, `work_plan_task`."""

    async def employee_of_user(self, user_id: UUID | str) -> Any:
        """employee_id milik akun, atau None."""
        row = await self.fetchone("SELECT employee_id FROM vms.app_user WHERE id = :uid", {"uid": user_id})
        return row.employee_id if row else None

    async def incidents_of_plan(self, plan_id: UUID | str, org_id: UUID | str) -> list[Any]:
        """Insiden satu SK beserta berkas buktinya, terbaru dulu."""
        return list(await self.fetchall(
            f"""
            SELECT ir.id, ir.work_plan_id, ir.reported_by, ir.occurred_on, ir.category, ir.severity,
                   ir.description, ir.status, ir.resolved_by, ir.resolved_at, ir.resolution_note, ir.created_at,
                   {_EVIDENCE_IDS.format(ref="ir.id")}
              FROM vms.incident_report ir
             WHERE ir.work_plan_id = :plan AND ir.organization_id = :org
             ORDER BY ir.created_at DESC
            """,
            {"plan": plan_id, "org": org_id}))

    async def insert_incident(self, org_id: UUID | str, plan_id: UUID | str, employee_id: Any, occurred_on: Any,
                              category: str, severity: str, description: str) -> Any:
        """Insiden baru."""
        return await self.fetchone(
            f"""
            INSERT INTO vms.incident_report (organization_id, work_plan_id, reported_by, occurred_on, category,
                                             severity, description)
            VALUES (:org, :plan, :emp, :occ, :cat, :sev, :desc)
            RETURNING {_INCIDENT_COLUMNS}
            """,
            {"org": org_id, "plan": plan_id, "emp": employee_id, "occ": occurred_on, "cat": category,
             "sev": severity, "desc": description})

    async def add_incident_evidence(self, incident_id: UUID | str, file_ids: list[str]) -> None:
        """Lampirkan berkas bukti ke insiden."""
        await self.execute(
            "INSERT INTO vms.incident_evidence (incident_id, file_id) SELECT :inc, unnest(CAST(:fids AS uuid[]))",
            {"inc": incident_id, "fids": file_ids})

    async def resolve_incident(self, incident_id: UUID | str, org_id: UUID | str, employee_id: Any,
                               note: str | None) -> Any:
        """Tandai insiden selesai. → baris (dengan bukti) atau None."""
        return await self.fetchone(
            f"""
            UPDATE vms.incident_report
               SET status = 'RESOLVED', resolved_by = :emp, resolved_at = now(), resolution_note = :note
             WHERE id = :id AND organization_id = :org
            RETURNING {_INCIDENT_COLUMNS}, {_EVIDENCE_IDS.format(ref="vms.incident_report.id")}
            """,
            {"emp": employee_id, "note": note, "id": incident_id, "org": org_id})

    async def upsert_daily_report(self, day_id: UUID | str, body: str | None, obstacle: str | None) -> Any:
        """Simpan draf — hanya selagi DRAFT / CHANGES_REQUESTED (V-24). → baris atau None bila terkunci."""
        return await self.fetchone(
            f"""
            INSERT INTO vms.daily_report (work_plan_day_id, body, obstacle)
            VALUES (:day, :body, :obs)
            ON CONFLICT (work_plan_day_id) DO UPDATE
               SET body = EXCLUDED.body, obstacle = EXCLUDED.obstacle, updated_at = now()
             WHERE vms.daily_report.status IN ('DRAFT', 'CHANGES_REQUESTED')
            RETURNING {_REPORT_COLUMNS}
            """,
            {"day": day_id, "body": body, "obs": obstacle})

    async def replace_report_evidence(self, report_id: UUID | str,
                                      items: list[tuple[str, str | None, str]]) -> None:
        """Ganti seluruh berkas bukti laporan harian: (file_id, slot_label, source)."""
        await self.execute("DELETE FROM vms.report_evidence WHERE daily_report_id = :rid", {"rid": report_id})
        if items:
            await self.execute(
                "INSERT INTO vms.report_evidence (daily_report_id, file_id, slot_label, source) "
                "SELECT :rid, CAST(f AS uuid), NULLIF(s, ''), src FROM unnest(CAST(:fids AS text[]), "
                "CAST(:slots AS text[]), CAST(:srcs AS text[])) AS t(f, s, src)",
                {"rid": report_id, "fids": [i[0] for i in items], "slots": [i[1] or "" for i in items],
                 "srcs": [i[2] for i in items]})

    async def submit_daily_report(self, day_id: UUID | str, employee_id: Any) -> Any:
        """Ajukan dari DRAFT atau setelah dikembalikan PM (V-24). → baris atau None."""
        return await self.fetchone(
            f"""
            UPDATE vms.daily_report
               SET status = 'SUBMITTED', submitted_by = :emp, submitted_at = now(),
                   resubmitted = resubmitted OR status = 'CHANGES_REQUESTED'   -- "Dikirim ulang" (alur SK v2)
             WHERE work_plan_day_id = :day AND status IN ('DRAFT', 'CHANGES_REQUESTED')
            RETURNING {_REPORT_COLUMNS}
            """,
            {"emp": employee_id, "day": day_id})

    async def review_daily_report(self, day_id: UUID | str, status: str, note: str | None,
                                  user_id: UUID | str) -> Any:
        """Setujui / kembalikan laporan SUBMITTED. → baris atau None."""
        return await self.fetchone(
            f"""
            UPDATE vms.daily_report
               SET status = CAST(:status AS vms.report_status), review_note = :note, reviewed_at = now(),
                   reviewed_by = (SELECT employee_id FROM vms.app_user WHERE id = :uid)
             WHERE work_plan_day_id = :day AND status = 'SUBMITTED'
            RETURNING {_REPORT_COLUMNS}
            """,
            {"status": status, "note": note, "uid": user_id, "day": day_id})

    async def daily_report_status(self, day_id: UUID | str) -> Any:
        """Status laporan harian hari itu, atau None bila belum ada."""
        row = await self.fetchone("SELECT status FROM vms.daily_report WHERE work_plan_day_id = :day",
                                  {"day": day_id})
        return row.status if row else None

    async def toggle_task(self, task_id: UUID | str, day_id: UUID | str, user_id: UUID | str) -> Any:
        """Balik centang tugas hari itu. → (id, is_done) atau None."""
        return await self.fetchone(
            """
            UPDATE vms.work_plan_task
               SET is_done = NOT is_done,
                   done_at = CASE WHEN is_done THEN NULL ELSE now() END,
                   done_by = CASE WHEN is_done THEN NULL
                                  ELSE (SELECT employee_id FROM vms.app_user WHERE id = :uid) END
             WHERE id = :task AND work_plan_day_id = :day
            RETURNING id, is_done
            """,
            {"task": task_id, "day": day_id, "uid": user_id})
