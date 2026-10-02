"""
app/crud/crud_notification.py
Notifikasi dalam aplikasi (alur SK v2): lonceng di web dan daftar di HP. Tanpa push (keputusan pemilik 2026-10-03).
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDNotification(CRUDBase):

    async def plan_people(self, plan_id: UUID | str) -> Any:
        """PM, ketua, dan anggota aktif sebuah SK — penerima notifikasi tahap SK."""
        return await self.fetchone(
            """
            SELECT wp.organization_id, wp.number, wp.title, CAST(wp.pm_employee_id AS text) AS pm,
                   CAST(wp.leader_employee_id AS text) AS leader,
                   COALESCE(ARRAY(SELECT CAST(m.employee_id AS text) FROM vms.work_plan_member m
                                   WHERE m.work_plan_id = wp.id AND upper_inf(m.valid_period)
                                     AND m.role_in_plan = 'MEMBER'), '{}') AS members
            FROM vms.work_plan wp WHERE wp.id = :plan
            """,
            {"plan": plan_id},
        )

    async def insert_many(self, org_id: UUID | str, recipients: Iterable[str], kind: str, title: str, body: str,
                          plan_id: UUID | str | None) -> None:
        ids = sorted({r for r in recipients if r})
        if not ids:
            return
        await self.execute(
            """
            INSERT INTO vms.notification (organization_id, recipient_employee_id, kind, title, body, work_plan_id)
            SELECT CAST(:org AS uuid), x, :kind, :title, :body, CAST(:plan AS uuid)
            FROM unnest(CAST(:ids AS uuid[])) AS x
            """,
            {"org": str(org_id), "ids": ids, "kind": kind, "title": title, "body": body,
             "plan": str(plan_id) if plan_id else None},
        )

    async def list_for(self, user_id: UUID | str, unread_only: bool, limit: int) -> list[Any]:
        return list(await self.fetchall(
            """
            SELECT n.id, n.kind, n.title, n.body, n.work_plan_id, n.created_at, n.read_at
            FROM vms.notification n
            JOIN vms.app_user u ON u.employee_id = n.recipient_employee_id
            WHERE u.id = CAST(:user AS uuid) AND (NOT CAST(:unread AS boolean) OR n.read_at IS NULL)
            ORDER BY n.created_at DESC
            LIMIT :limit
            """,
            {"user": str(user_id), "unread": unread_only, "limit": limit},
        ))

    async def unread_count(self, user_id: UUID | str) -> int:
        value = await self.scalar(
            """
            SELECT count(*) FROM vms.notification n JOIN vms.app_user u ON u.employee_id = n.recipient_employee_id
            WHERE u.id = CAST(:user AS uuid) AND n.read_at IS NULL
            """,
            {"user": str(user_id)},
        )
        return int(value or 0)

    async def mark_read(self, user_id: UUID | str, notification_id: UUID | str | None) -> int:
        """Tandai satu (atau semua bila `notification_id` None) notifikasi milik pengguna sebagai dibaca."""
        result = await self.execute(
            """
            UPDATE vms.notification n SET read_at = now()
              FROM vms.app_user u
             WHERE u.id = CAST(:user AS uuid) AND n.recipient_employee_id = u.employee_id AND n.read_at IS NULL
               AND (CAST(:id AS uuid) IS NULL OR n.id = CAST(:id AS uuid))
            """,
            {"user": str(user_id), "id": str(notification_id) if notification_id else None},
        )
        return int(result.rowcount or 0)
