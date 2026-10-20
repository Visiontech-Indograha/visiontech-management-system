"""
app/modules/notifications/repositories/notification_repository.py
Notifikasi realtime (event SSE) Master Schema V2 — tanpa tabel kotak masuk.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from app.core.events import queue_event
from app.core.repository import BaseRepository


class NotificationRepository(BaseRepository):
    """Penerima notifikasi & penyiaran event realtime."""

    async def daily_people(self, daily_plan_id: UUID | str) -> Any:
        """PM/OM divisi, pembuat, ketua, dan anggota aktif sebuah jadwal harian (employee_id teks)."""
        return await self.fetchone(
            """
            SELECT t.office_id, t.name AS team_name, wpd.work_date, wpd.site_name,
                   CAST(d.pm_id AS text) AS pm, CAST(d.om_id AS text) AS om,
                   CAST(wpd.created_by_id AS text) AS creator, CAST(t.leader_employee_id AS text) AS leader,
                   COALESCE(ARRAY(SELECT CAST(m.employee_id AS text) FROM member m
                                  WHERE m.team_id = wpd.team_id AND m.is_active AND m.delete_at IS NULL), '{}')
                       AS members
            FROM work_plan_daily wpd
            JOIN division d ON d.division_id = wpd.division_id
            JOIN team t ON t.team_id = wpd.team_id
            WHERE wpd.daily_plan_id = CAST(:id AS uuid)
            """,
            {"id": str(daily_plan_id)},
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
                {"kind": kind, "title": title, "body": body, "daily_plan_id": str(plan_id) if plan_id else None},
            )
            if plan_id:
                queue_event(self.db, users, "plan", {"daily_plan_id": str(plan_id)})

    async def list_for(self, user_id: UUID | str, unread_only: bool, limit: int) -> list[Any]:
        """Mengambil daftar notifikasi untuk pengguna tertentu."""
        return []

    async def unread_count(self, user_id: UUID | str) -> int:
        """Menghitung jumlah notifikasi yang belum dibaca."""
        return 0

    async def mark_read(self, user_id: UUID | str, notification_id: UUID | str | None) -> int:
        """Tandai notifikasi sebagai dibaca."""
        return 0

