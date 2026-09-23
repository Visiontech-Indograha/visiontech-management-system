"""
app/repositories/plan_repo.py
Query untuk work_plan, work_plan_day, work_plan_task, work_plan_member, plan_document.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base_repo import BaseRepo


class PlanRepo(BaseRepo):

    async def get_by_id(self, plan_id: UUID, org_id: UUID) -> Any:
        return await self.fetchone(
            """
            SELECT * FROM vms.work_plan
            WHERE id = :id AND organization_id = :org AND deleted_at IS NULL
            """,
            {"id": plan_id, "org": org_id},
        )

    async def get_by_id_for_update(self, plan_id: UUID, org_id: UUID) -> Any:
        return await self.fetchone(
            """
            SELECT * FROM vms.work_plan
            WHERE id = :id AND organization_id = :org AND deleted_at IS NULL
            FOR UPDATE
            """,
            {"id": plan_id, "org": org_id},
        )

    async def list_plans(
        self,
        org_id: UUID,
        status: str | None = None,
        limit: int = 20,
        cursor_created_at: str | None = None,
    ) -> list[Any]:
        where = "organization_id = :org AND deleted_at IS NULL"
        params: dict[str, Any] = {"org": org_id, "limit": limit}
        if status:
            where += " AND status = :status"
            params["status"] = status
        if cursor_created_at:
            where += " AND created_at < :cursor"
            params["cursor"] = cursor_created_at
        return await self.fetchall(
            f"SELECT * FROM vms.work_plan WHERE {where} ORDER BY created_at DESC LIMIT :limit",
            params,
        )

    async def create_plan(self, org_id: UUID, data: dict[str, Any]) -> Any:
        return await self.fetchone(
            """
            INSERT INTO vms.work_plan (
                organization_id, title, description, business_unit_id,
                period, leader_employee_id, budget
            ) VALUES (
                :org, :title, :desc, :unit,
                daterange(:start, :end, '[]'), :leader, :budget
            ) RETURNING *
            """,
            {
                "org": org_id, "title": data["title"], "desc": data.get("description"),
                "unit": data.get("business_unit_id"), "start": data["period_start"],
                "end": data["period_end"], "leader": data.get("leader_employee_id"),
                "budget": data.get("budget"),
            },
        )

    async def update_status(
        self,
        plan_id: UUID,
        new_status: str,
        row_version: int,
        extra_fields: dict[str, Any] | None = None,
    ) -> Any:
        """
        Update status dengan optimistic lock. Kembalikan None jika row_version tidak cocok
        (berarti ada pengeditan bersamaan → ConflictError di service).
        """
        sets = "status = :status, row_version = row_version + 1"
        params: dict[str, Any] = {
            "id": plan_id, "status": new_status, "rv": row_version,
        }
        if extra_fields:
            for k, v in extra_fields.items():
                sets += f", {k} = :{k}"
                params[k] = v
        return await self.fetchone(
            f"""
            UPDATE vms.work_plan SET {sets}
            WHERE id = :id AND row_version = :rv AND deleted_at IS NULL
            RETURNING *
            """,
            params,
        )

    async def create_document_snapshot(
        self,
        plan_id: UUID,
        kind: str,
        version: int,
        number: str,
        snapshot_json: str,
        snapshot_sha: bytes,
        issued_by: UUID,
        status: str = "AWAITING_ACCEPTANCE",
    ) -> Any:
        return await self.fetchone(
            """
            INSERT INTO vms.plan_document (
                work_plan_id, kind, version, number, status,
                snapshot, snapshot_sha256, issued_by
            ) VALUES (
                :plan_id, :kind, :ver, :num, :status,
                :snap::jsonb, :hash, :emp
            ) RETURNING id
            """,
            {
                "plan_id": plan_id, "kind": kind, "ver": version, "num": number,
                "status": status, "snap": snapshot_json, "hash": snapshot_sha,
                "emp": issued_by,
            },
        )

    async def get_snapshot(self, plan_id: UUID) -> Any:
        """Ambil data lengkap untuk snapshot SK."""
        return await self.fetchone(
            """
            SELECT
                wp.*,
                (SELECT json_agg(row_to_json(wpm))
                 FROM vms.work_plan_member wpm WHERE wpm.work_plan_id = wp.id) AS members,
                (SELECT json_agg(row_to_json(wpd) ORDER BY wpd.day_date)
                 FROM vms.work_plan_day wpd WHERE wpd.work_plan_id = wp.id) AS days
            FROM vms.work_plan wp WHERE wp.id = :id
            """,
            {"id": plan_id},
        )

    async def list_days(self, plan_id: UUID) -> list[Any]:
        return await self.fetchall(
            """
            SELECT wpd.*, json_agg(row_to_json(wpt) ORDER BY wpt.sort_order) AS tasks
            FROM vms.work_plan_day wpd
            LEFT JOIN vms.work_plan_task wpt ON wpt.work_plan_day_id = wpd.id
            WHERE wpd.work_plan_id = :plan
            GROUP BY wpd.id ORDER BY wpd.day_date
            """,
            {"plan": plan_id},
        )
