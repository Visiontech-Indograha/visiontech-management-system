"""
app/repositories/plan_transition_repo.py
Kueri untuk transisi SK (publish, accept, start). Satu-satunya tempat SQL-nya (dok 12).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.enums import DocumentKind, DocumentStatus, PlanStatus

from .base_repo import BaseRepo

# Daftar kolom ditulis ulang di setiap kueri (bukan disambung) agar tiap kueri tetap literal statis
# yang diperiksa terhadap skema oleh tests/test_sql_matches_schema.py.


class PlanTransitionRepo(BaseRepo):

    async def lock_plan(self, plan_id: UUID | str, org_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT id, unit_id, site_id, number, title, location_text, description,
                   lower(period) AS period_start, upper(period) - 1 AS period_end,
                   status, pm_employee_id, leader_employee_id, revision, row_version, cancellation_reason
            FROM vms.work_plan
            WHERE id = :id AND organization_id = :org AND deleted_at IS NULL
            FOR UPDATE
            """,
            {"id": plan_id, "org": org_id},
        )

    async def get_plan(self, plan_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT id, unit_id, site_id, number, title, location_text, description,
                   lower(period) AS period_start, upper(period) - 1 AS period_end,
                   status, pm_employee_id, leader_employee_id, revision, row_version, cancellation_reason
            FROM vms.work_plan WHERE id = :id
            """,
            {"id": plan_id},
        )

    async def active_team(self, plan_id: UUID | str) -> list[Any]:
        """Anggota aktif (valid_period terbuka) beserta status karyawannya."""
        return list(await self.fetchall(
            """
            SELECT m.employee_id::text AS employee_id, m.role_in_plan::text AS role_in_plan,
                   e.is_active AND e.deleted_at IS NULL AS employee_active
            FROM vms.work_plan_member m JOIN vms.employee e ON e.id = m.employee_id
            WHERE m.work_plan_id = :plan AND upper_inf(m.valid_period)
            """,
            {"plan": plan_id},
        ))

    async def day_details_complete(self, plan_id: UUID | str) -> bool:
        """Setiap tanggal periode punya hari berjudul dengan ≥ 1 tugas berjudul (domain.js PUBLISH)."""
        return bool(await self.scalar(
            """
            SELECT
              (SELECT count(*) FROM vms.work_plan_day d
                 WHERE d.work_plan_id = wp.id AND d.work_date <@ wp.period
                   AND btrim(d.title) <> ''
                   AND EXISTS (SELECT 1 FROM vms.work_plan_task t WHERE t.work_plan_day_id = d.id)
                   AND NOT EXISTS (SELECT 1 FROM vms.work_plan_task t
                                   WHERE t.work_plan_day_id = d.id AND btrim(t.title) = ''))
              = (upper(wp.period) - lower(wp.period))
            FROM vms.work_plan wp WHERE wp.id = :plan
            """,
            {"plan": plan_id},
        ))

    async def snapshot(self, plan_id: UUID | str) -> Any:
        """Isi beku dokumen: SK, tim aktif, hari beserta tugasnya (domain.js snapshot)."""
        return await self.scalar(
            """
            SELECT jsonb_build_object(
              'plan', (SELECT to_jsonb(p) - 'row_version' FROM (
                  SELECT id, unit_id, site_id, number, title, location_text, description,
                   lower(period) AS period_start, upper(period) - 1 AS period_end,
                   status, pm_employee_id, leader_employee_id, revision, row_version, cancellation_reason
                  FROM vms.work_plan WHERE id = :plan) p),
              'team', COALESCE((SELECT jsonb_agg(jsonb_build_object('employee_id', m.employee_id,
                                        'full_name', e.full_name, 'role_in_plan', m.role_in_plan)
                                        ORDER BY m.role_in_plan, e.full_name)
                                FROM vms.work_plan_member m JOIN vms.employee e ON e.id = m.employee_id
                                WHERE m.work_plan_id = :plan AND upper_inf(m.valid_period)), '[]'),
              'days', COALESCE((SELECT jsonb_agg(jsonb_build_object('work_date', d.work_date, 'title', d.title,
                                        'tasks', (SELECT COALESCE(jsonb_agg(t.title ORDER BY t.sort_order, t.title), '[]')
                                                  FROM vms.work_plan_task t WHERE t.work_plan_day_id = d.id))
                                        ORDER BY d.work_date)
                                FROM vms.work_plan_day d WHERE d.work_plan_id = :plan), '[]')
            )
            """,
            {"plan": plan_id},
        )

    async def employee_id_of(self, user_id: UUID | str) -> str | None:
        value = await self.scalar("SELECT employee_id::text FROM vms.app_user WHERE id = :uid", {"uid": user_id})
        return str(value) if value else None

    async def is_leader(self, plan_id: UUID | str, user_id: UUID | str) -> bool:
        return bool(await self.scalar("SELECT vms.is_plan_leader(:plan, :user)", {"plan": plan_id, "user": user_id}))

    async def publish(self, plan_id: UUID | str) -> None:
        # Nomor SK sementara; format resmi ditetapkan fase 6 dari contoh dokumen perusahaan (K-14).
        await self.execute(
            """
            UPDATE vms.work_plan
               SET status = :published, row_version = row_version + 1,
                   number = COALESCE(number, 'SK-' || to_char(CURRENT_DATE, 'YYYYMM') || '-' || substr(id::text, 1, 8))
             WHERE id = :plan
            """,
            {"plan": plan_id, "published": PlanStatus.PUBLISHED},
        )

    async def insert_document(self, plan_id: UUID | str, revision: int, snapshot: Any, issued_by: str) -> None:
        await self.execute(
            """
            INSERT INTO vms.plan_document (work_plan_id, kind, version, number, status, snapshot, snapshot_sha256, issued_by)
            SELECT id, CAST(:kind AS vms.document_kind), :version, number, CAST(:status AS vms.document_status),
                   CAST(:snapshot AS jsonb), ''::bytea, :issued_by   -- hash dihitung trigger plan_document_hash
            FROM vms.work_plan WHERE id = :plan
            """,
            {
                "plan": plan_id, "version": revision, "snapshot": snapshot, "issued_by": issued_by,
                "kind": DocumentKind.INITIAL_ORDER if revision == 1 else DocumentKind.REVISION,
                "status": DocumentStatus.AWAITING_ACCEPTANCE,
            },
        )

    async def set_status(self, plan_id: UUID | str, status: PlanStatus) -> None:
        await self.execute(
            "UPDATE vms.work_plan SET status = CAST(:status AS vms.plan_status), row_version = row_version + 1 WHERE id = :plan",
            {"plan": plan_id, "status": status},
        )

    async def accept_document(self, plan_id: UUID | str, employee_id: str) -> None:
        await self.execute(
            """
            UPDATE vms.plan_document SET status = :effective, accepted_by = :emp, accepted_at = now()
             WHERE work_plan_id = :plan AND status = :awaiting
            """,
            {"plan": plan_id, "emp": employee_id, "effective": DocumentStatus.EFFECTIVE,
             "awaiting": DocumentStatus.AWAITING_ACCEPTANCE},
        )
