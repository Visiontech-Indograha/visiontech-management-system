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

    async def user_ids_for_employees(self, employee_ids: Iterable[str]) -> list[str]:
        """Akun pengguna aktif milik sekumpulan karyawan."""
        ids = sorted({r for r in employee_ids if r})
        if not ids:
            return []
        rows = await self.fetchall(
            "SELECT CAST(user_id AS text) AS id FROM users "
            "WHERE employee_id = ANY(CAST(:ids AS uuid[])) AND delete_at IS NULL",
            {"ids": ids},
        )
        return [str(r.id) for r in rows]

    async def user_ids_with_role(
        self, roles: Iterable[str], office_id: UUID | str | None = None, division_id: UUID | str | None = None
    ) -> list[str]:
        """Akun aktif dengan salah satu peran; opsional dibatasi kantor/divisi."""
        rows = await self.fetchall(
            "SELECT CAST(u.user_id AS text) AS id FROM users u LEFT JOIN employee e ON e.employee_id = u.employee_id "
            "WHERE CAST(u.system_role AS text) = ANY(CAST(:roles AS text[])) AND u.is_active AND u.delete_at IS NULL "
            "AND (CAST(:office AS uuid) IS NULL OR e.office_id = CAST(:office AS uuid)) "
            "AND (CAST(:division AS uuid) IS NULL OR e.division_id = CAST(:division AS uuid))",
            {
                "roles": sorted(set(roles)),
                "office": str(office_id) if office_id else None,
                "division": str(division_id) if division_id else None,
            },
        )
        return [str(r.id) for r in rows]

    async def hr_user_ids_for_office(self, office_id: UUID | str | None) -> list[str]:
        """Akun aktif ADMIN_HR_GA yang jangkauannya meliputi `office_id`: kantor sendiri atau penugasan HR aktif
        (ADR 0002). Aset tanpa kantor tidak dijangkau HR terbatas mana pun."""
        if not office_id:
            return []
        rows = await self.fetchall(
            "SELECT DISTINCT CAST(u.user_id AS text) AS id FROM users u "
            "LEFT JOIN employee e ON e.employee_id = u.employee_id AND e.delete_at IS NULL "
            "WHERE u.is_active AND u.delete_at IS NULL AND ("
            " (CAST(u.system_role AS text) = 'ADMIN_HR_GA' AND e.office_id = CAST(:office AS uuid))"
            " OR EXISTS (SELECT 1 FROM user_role_assignment a JOIN office o ON o.office_id = a.office_id "
            "   AND o.delete_at IS NULL WHERE a.user_id = u.user_id AND a.delete_at IS NULL "
            "   AND CAST(a.role AS text) = 'ADMIN_HR_GA' AND a.office_id = CAST(:office AS uuid)))",
            {"office": str(office_id)},
        )
        return [str(r.id) for r in rows]

    async def division_manager_user_ids(self, division_id: UUID | str, roles: Iterable[str]) -> list[str]:
        """Akun PM/OM yang tercatat di divisi itu (division.pm_id / om_id), bukan divisi 'rumah' karyawannya:
        PM yang memimpin beberapa divisi tetap menerima notifikasi tiap divisinya."""
        rows = await self.fetchall(
            "SELECT DISTINCT CAST(u.user_id AS text) AS id FROM division d "
            "JOIN users u ON u.employee_id IN (d.pm_id, d.om_id) "
            "WHERE d.division_id = CAST(:div AS uuid) AND d.delete_at IS NULL "
            "AND u.is_active AND u.delete_at IS NULL "
            "AND CAST(u.system_role AS text) = ANY(CAST(:roles AS text[]))",
            {"div": str(division_id), "roles": sorted(set(roles))},
        )
        return [str(r.id) for r in rows]

    async def employee_name(self, employee_id: UUID | str) -> str:
        """Nama lengkap karyawan (untuk judul notifikasi)."""
        name = await self.scalar(
            "SELECT full_name FROM employee WHERE employee_id = CAST(:e AS uuid)", {"e": str(employee_id)}
        )
        return str(name) if name else "Karyawan"

    async def employee_division(self, employee_id: UUID | str) -> Any:
        """Kantor dan divisi akun karyawan (penerima persetujuan sebatas divisinya)."""
        return await self.fetchone(
            "SELECT office_id, division_id FROM employee WHERE employee_id = CAST(:e AS uuid) AND delete_at IS NULL",
            {"e": str(employee_id)},
        )

    async def insert_for_users(
        self,
        user_ids: Iterable[str],
        kind: str,
        title: str,
        body: str,
        plan_id: UUID | str | None,
        target: str | None,
    ) -> None:
        """Simpan ke kotak masuk lalu siarkan lewat SSE (pengguna offline tetap melihatnya nanti)."""
        users = sorted({u for u in user_ids if u})
        if not users:
            return
        await self.execute(
            "INSERT INTO notification (user_id, kind, title, body, daily_plan_id, target) "
            "SELECT us.user_id, :kind, :title, :body, CAST(:plan AS uuid), :target "
            "FROM users us WHERE us.user_id = ANY(CAST(:users AS uuid[])) AND us.delete_at IS NULL "
            "FOR KEY SHARE OF us",
            {
                "kind": kind[:40],
                "title": title[:200],
                "body": body,
                "plan": str(plan_id) if plan_id else None,
                "target": target,
                "users": users,
            },
        )
        queue_event(
            self.db,
            users,
            "notification",
            {
                "kind": kind, "title": title, "body": body,
                "daily_plan_id": str(plan_id) if plan_id else None, "target": target,
            },
        )
        if plan_id:
            queue_event(self.db, users, "plan", {"daily_plan_id": str(plan_id)})

    async def insert_many(
        self,
        org_id: UUID | str,
        recipients: Iterable[str],
        kind: str,
        title: str,
        body: str,
        plan_id: UUID | str | None,
        target: str | None = None,
    ) -> None:
        """Notifikasi untuk karyawan (employee_id): disimpan dan disiarkan."""
        target = target or ("attendance" if kind.startswith("ATTENDANCE") else None)
        await self.insert_for_users(await self.user_ids_for_employees(recipients), kind, title, body, plan_id, target)

    async def list_for(self, user_id: UUID | str, unread_only: bool, limit: int) -> list[Any]:
        """Notifikasi milik pengguna, terbaru dulu."""
        return list(
            await self.fetchall(
                "SELECT notification_id AS id, kind, title, body, daily_plan_id, target, "
                "create_at AS created_at, read_at "
                "FROM notification WHERE user_id = CAST(:u AS uuid) AND (NOT :unread OR read_at IS NULL) "
                "ORDER BY create_at DESC LIMIT :n",
                {"u": str(user_id), "unread": unread_only, "n": limit},
            )
        )

    async def unread_count(self, user_id: UUID | str) -> int:
        """Jumlah notifikasi belum dibaca."""
        return int(
            await self.scalar(
                "SELECT COUNT(*) FROM notification WHERE user_id = CAST(:u AS uuid) AND read_at IS NULL",
                {"u": str(user_id)},
            )
            or 0
        )

    async def mark_read(self, user_id: UUID | str, notification_id: UUID | str | None) -> int:
        """Tandai satu/semua notifikasi pengguna sebagai dibaca."""
        res = await self.execute(
            "UPDATE notification SET read_at = NOW() WHERE user_id = CAST(:u AS uuid) AND read_at IS NULL "
            "AND (CAST(:nid AS uuid) IS NULL OR notification_id = CAST(:nid AS uuid))",
            {"u": str(user_id), "nid": str(notification_id) if notification_id else None},
        )
        return int(getattr(res, "rowcount", 0) or 0)
