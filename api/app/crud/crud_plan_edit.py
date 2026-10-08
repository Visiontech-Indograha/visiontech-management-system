"""
app/crud/crud_plan_edit.py
Penyusunan draf SK jalur lama (POST /work-plans, PATCH, hari & tugas). Form lengkap v2 ada di crud_plan_draft.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase

_PLAN_COLUMNS = """id, unit_id, site_id, number, title, location_text, description,
                   lower(period) AS period_start, upper(period) - integer '1' AS period_end,
                   status, pm_employee_id, leader_employee_id, revision, row_version, cancellation_reason"""


class CRUDPlanEdit(CRUDBase):
    """Kueri `work_plan`, `work_plan_member` (ketua), `work_plan_day`, `work_plan_task` untuk draf."""

    async def insert_plan(self, org_id: UUID | str, *, unit_id: Any, site_id: Any, title: str,
                          location_text: str | None, description: str | None, period_start: Any, period_end: Any,
                          pm_employee_id: Any, leader_employee_id: Any) -> Any:
        """Draf SK baru. → (id, number, status, revision, row_version, cancellation_reason)."""
        return await self.fetchone(
            """
            INSERT INTO vms.work_plan (organization_id, unit_id, site_id, title, location_text, description,
                                       period, pm_employee_id, leader_employee_id, status)
            VALUES (:org, :unit, :site, :title, :loc, :desc, daterange(:start, :end, '[]'), :pm, :leader, 'DRAFT')
            RETURNING id, number, status, revision, row_version, cancellation_reason
            """,
            {"org": org_id, "unit": unit_id, "site": site_id, "title": title, "loc": location_text,
             "desc": description, "start": period_start, "end": period_end, "pm": pm_employee_id,
             "leader": leader_employee_id})

    async def add_leader(self, plan_id: UUID | str, employee_id: Any, start: Any) -> None:
        """Ketua sebagai anggota SK, berlaku sejak `start` dan terbuka (= aktif, is_plan_member)."""
        await self.execute(
            """
            INSERT INTO vms.work_plan_member (work_plan_id, employee_id, role_in_plan, valid_period)
            VALUES (:plan, :emp, 'LEADER', daterange(CAST(:start AS date), NULL, '[)'))
            """,
            {"plan": plan_id, "emp": employee_id, "start": start})

    async def remove_leader(self, plan_id: UUID | str) -> None:
        """Hapus baris ketua lama (draf)."""
        await self.execute("DELETE FROM vms.work_plan_member WHERE work_plan_id = :plan AND role_in_plan = 'LEADER'",
                           {"plan": plan_id})

    async def draft_state(self, plan_id: UUID | str, org_id: UUID | str) -> Any:
        """Status, versi, ketua, periode, unit SK organisasi ini, atau None."""
        return await self.fetchone(
            """
            SELECT status, row_version, pm_employee_id, leader_employee_id, lower(period) AS period_start,
                   upper(period) - integer '1' AS period_end, unit_id
              FROM vms.work_plan WHERE id = :id AND organization_id = :org
            """,
            {"id": plan_id, "org": org_id})

    async def update_plan(self, plan_id: UUID | str, org_id: UUID | str, version: int, sets: list[str],
                          params: dict[str, Any]) -> Any:
        """Ubah draf dengan optimistic locking. `sets` disusun service dari kolom tetap. → baris atau None."""
        return await self.fetchone(
            f"""
            UPDATE vms.work_plan SET {", ".join(sets)}
             WHERE id = :id AND organization_id = :org AND row_version = :version
            RETURNING {_PLAN_COLUMNS}
            """,
            {"id": plan_id, "org": org_id, "version": version, **params})

    async def plan_status(self, plan_id: UUID | str, org_id: UUID | str) -> Any:
        """Status SK organisasi ini, atau None."""
        row = await self.fetchone("SELECT status FROM vms.work_plan WHERE id = :id AND organization_id = :org",
                                  {"id": plan_id, "org": org_id})
        return row.status if row else None

    async def insert_day(self, plan_id: UUID | str, work_date: Any, title: str | None, sort_order: int) -> Any:
        """Hari baru pada SK. → id."""
        row = await self.fetchone(
            "INSERT INTO vms.work_plan_day (work_plan_id, work_date, title, sort_order) "
            "VALUES (:plan, :date, :title, :sort) RETURNING id",
            {"plan": plan_id, "date": work_date, "title": title, "sort": sort_order})
        return row.id

    async def insert_task(self, day_id: UUID | str, title: str, sort_order: int) -> Any:
        """Tugas baru pada hari. → id."""
        row = await self.fetchone(
            "INSERT INTO vms.work_plan_task (work_plan_day_id, title, sort_order) VALUES (:day, :title, :sort) "
            "RETURNING id",
            {"day": day_id, "title": title, "sort": sort_order})
        return row.id

    async def replace_day_plan(self, day_id: UUID | str, title: str, task_titles: list[str]) -> None:
        """Ganti judul hari & seluruh tugasnya (urutan sesuai daftar)."""
        await self.execute("UPDATE vms.work_plan_day SET title = :title WHERE id = :day",
                           {"title": title, "day": day_id})
        await self.execute("DELETE FROM vms.work_plan_task WHERE work_plan_day_id = :day", {"day": day_id})
        if task_titles:
            await self.execute(
                """
                INSERT INTO vms.work_plan_task (work_plan_day_id, title, sort_order)
                SELECT :day, u.title, u.sort
                  FROM unnest(CAST(:titles AS text[]), CAST(:sorts AS int[])) AS u(title, sort)
                """,
                {"day": day_id, "titles": task_titles, "sorts": list(range(len(task_titles)))})
