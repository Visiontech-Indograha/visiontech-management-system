"""
app/crud/crud_notification.py
Notifikasi dalam aplikasi untuk Master Schema V2.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from app.core.events import queue_event

from .base import CRUDBase


class CRUDNotification(CRUDBase):
    """
    Kelas CRUD untuk mengelola data notifikasi dan event realtime.
    """

    async def plan_people(self, plan_id: UUID | str) -> Any:
        """PM, ketua, dan anggota sebuah SK mingguan."""
        return await self.fetchone(
            """
            SELECT t.office_id AS organization_id,
                   'SK/W' || wp.week_number || '/' || wp.year AS number,
                   'Rencana Kerja Mingguan W' || wp.week_number || ' - ' || t.name AS title,
                   CAST(COALESCE(wp.approved_by_pm_id, div.pm_id) AS text) AS pm,
                   CAST(t.leader_employee_id AS text) AS leader,
                   wp.start_date AS period_start,
                   wp.end_date AS period_end,
                   COALESCE(ARRAY(
                       SELECT CAST(m.employee_id AS text) FROM member m
                       WHERE m.team_id = wp.team_id AND m.is_active = TRUE AND m.delete_at IS NULL
                   ), '{}') AS members
            FROM work_plan_weekly wp
            JOIN division div ON div.division_id = wp.division_id
            JOIN team t ON t.team_id = wp.team_id
            WHERE wp.weekly_plan_id = CAST(:plan AS uuid)
            """,
            {"plan": str(plan_id)},
        )

    async def insert_many(
        self,
        org_id: UUID | str,
        recipients: Iterable[str],
        kind: str,
        title: str,
        body: str,
        plan_id: UUID | str | None,
    ) -> None:
        """Menyiarkan notifikasi ke user via realtime event queue."""
        ids = sorted({r for r in recipients if r})
        if not ids:
            return

        users = [
            str(r.id)
            for r in await self.fetchall(
                "SELECT user_id AS id FROM users WHERE employee_id = ANY(CAST(:ids AS uuid[])) AND delete_at IS NULL",
                {"ids": ids},
            )
        ]
        if users:
            queue_event(
                self.db,
                users,
                "notification",
                {"kind": kind, "title": title, "body": body, "plan_id": str(plan_id) if plan_id else None},
            )
            if plan_id:
                queue_event(self.db, users, "plan", {"plan_id": str(plan_id)})

    async def list_for(self, user_id: UUID | str, unread_only: bool, limit: int) -> list[Any]:
        """Mengambil daftar notifikasi untuk pengguna tertentu."""
        return []

    async def unread_count(self, user_id: UUID | str) -> int:
        """Menghitung jumlah notifikasi yang belum dibaca."""
        return 0

    async def mark_read(self, user_id: UUID | str, notification_id: UUID | str | None) -> int:
        """Tandai notifikasi sebagai dibaca."""
        return 0
