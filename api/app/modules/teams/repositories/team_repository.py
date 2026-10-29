"""
app/modules/teams/repositories/team_repository.py
Akses data tim lapangan dan anggotanya (Master Schema V2).

Relasi: team N─1 office, team N─1 division, team N─1 employee (leader_employee_id),
team 1─N member, member N─1 employee. Hapus = soft delete (`delete_at`).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_TEAM_COLUMNS = """
    t.team_id, t.office_id, t.division_id, t.leader_employee_id, t.name, t.status, t.create_at,
    e.full_name AS leader_name, d.name AS division_name, o.name AS office_name,
    (SELECT COUNT(*)::int FROM member m
      WHERE m.team_id = t.team_id AND m.delete_at IS NULL AND m.is_active) AS member_count
"""
_TEAM_FROM = """
    FROM team t
    JOIN employee e ON e.employee_id = t.leader_employee_id
    JOIN division d ON d.division_id = t.division_id
    JOIN office o ON o.office_id = t.office_id
"""


class TeamRepository(BaseRepository):
    """Query tim (team) dan keanggotaannya (member)."""

    async def list_teams(self, division_id: UUID | None = None, pm_employee_id: UUID | str | None = None) -> list[Any]:
        """Tim belum dihapus; opsional dibatasi satu divisi dan/atau divisi milik PM tertentu."""
        sql = f"SELECT {_TEAM_COLUMNS} {_TEAM_FROM} WHERE t.delete_at IS NULL"
        params: dict[str, Any] = {}
        if division_id is not None:
            sql += " AND t.division_id = CAST(:div AS uuid)"
            params["div"] = str(division_id)
        if pm_employee_id is not None:
            sql += " AND d.pm_id = CAST(:pm AS uuid)"
            params["pm"] = str(pm_employee_id)
        return list(await self.fetchall(sql + " ORDER BY d.name, t.name", params))

    async def get(self, team_id: UUID | str) -> Any:
        return await self.fetchone(
            f"SELECT {_TEAM_COLUMNS}, d.pm_id {_TEAM_FROM} WHERE t.team_id = CAST(:id AS uuid) AND t.delete_at IS NULL",
            {"id": str(team_id)},
        )

    async def members(self, team_id: UUID | str) -> list[Any]:
        """Anggota aktif tim beserta peran akunnya."""
        return list(
            await self.fetchall(
                """
                SELECT m.member_id, m.team_id, m.employee_id, m.is_active, m.create_at,
                       e.full_name, e.employee_no, e.phone_number, u.system_role::text AS system_role,
                       (SELECT f.id FROM file_object f WHERE f.storage_key = e.profile_photo_path LIMIT 1)
                           AS photo_file_id
                FROM member m
                JOIN employee e ON e.employee_id = m.employee_id
                LEFT JOIN users u ON u.employee_id = e.employee_id AND u.delete_at IS NULL
                WHERE m.team_id = CAST(:id AS uuid) AND m.delete_at IS NULL AND m.is_active
                ORDER BY (m.employee_id = (SELECT leader_employee_id FROM team WHERE team_id = m.team_id)) DESC,
                         e.full_name
                """,
                {"id": str(team_id)},
            )
        )

    async def employee_role(self, employee_id: UUID | str) -> str | None:
        """system_role karyawan aktif (employee 1─1 users); None bila tidak ada/nonaktif/offboarding."""
        role: str | None = await self.scalar(
            """
            SELECT u.system_role::text
            FROM employee e
            JOIN users u ON u.employee_id = e.employee_id AND u.delete_at IS NULL AND u.is_active
            WHERE e.employee_id = CAST(:emp AS uuid) AND e.delete_at IS NULL
              AND e.offboarding_status = 'active'
            """,
            {"emp": str(employee_id)},
        )
        return role

    async def division(self, division_id: UUID | str) -> Any:
        """Divisi aktif (status TRUE, belum dihapus) beserta PM-nya, atau None."""
        return await self.fetchone(
            "SELECT division_id, pm_id FROM division "
            "WHERE division_id = CAST(:id AS uuid) AND delete_at IS NULL AND status",
            {"id": str(division_id)},
        )

    async def office_active(self, office_id: UUID | str) -> bool:
        return bool(
            await self.scalar(
                "SELECT EXISTS (SELECT 1 FROM office WHERE office_id = CAST(:id AS uuid) AND delete_at IS NULL)",
                {"id": str(office_id)},
            )
        )

    async def name_taken(self, division_id: UUID | str, name: str, exclude: UUID | str | None = None) -> bool:
        """Nama tim unik per divisi (tanpa membedakan huruf besar/kecil)."""
        return bool(
            await self.scalar(
                """
                SELECT EXISTS (
                    SELECT 1 FROM team
                    WHERE division_id = CAST(:div AS uuid) AND lower(name) = lower(:name) AND delete_at IS NULL
                      AND (CAST(:ex AS uuid) IS NULL OR team_id <> CAST(:ex AS uuid))
                )
                """,
                {"div": str(division_id), "name": name, "ex": str(exclude) if exclude else None},
            )
        )

    async def insert(self, office_id: UUID, division_id: UUID, leader_id: UUID, name: str, status: bool) -> UUID:
        team_id: UUID = await self.scalar(
            """
            INSERT INTO team (office_id, division_id, leader_employee_id, name, status)
            VALUES (CAST(:office AS uuid), CAST(:div AS uuid), CAST(:leader AS uuid), :name, :status)
            RETURNING team_id
            """,
            {"office": str(office_id), "div": str(division_id), "leader": str(leader_id), "name": name,
             "status": status},
        )
        return team_id

    async def update(
        self,
        team_id: UUID | str,
        *,
        office_id: UUID | None,
        division_id: UUID | None,
        leader_id: UUID | None,
        name: str | None,
        status: bool | None,
    ) -> None:
        await self.execute(
            """
            UPDATE team SET
                office_id = COALESCE(CAST(:office AS uuid), office_id),
                division_id = COALESCE(CAST(:div AS uuid), division_id),
                leader_employee_id = COALESCE(CAST(:leader AS uuid), leader_employee_id),
                name = COALESCE(:name, name),
                status = COALESCE(CAST(:status AS boolean), status),
                update_at = now()
            WHERE team_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {"id": str(team_id), "office": str(office_id) if office_id else None,
             "div": str(division_id) if division_id else None, "leader": str(leader_id) if leader_id else None,
             "name": name, "status": status},
        )

    async def plan_count(self, team_id: UUID | str) -> int:
        """Jumlah jadwal harian (work_plan_daily N─1 team) yang masih merujuk tim ini."""
        return int(
            await self.scalar(
                "SELECT COUNT(*) FROM work_plan_daily WHERE team_id = CAST(:id AS uuid) AND delete_at IS NULL",
                {"id": str(team_id)},
            )
            or 0
        )

    async def archive(self, team_id: UUID | str) -> None:
        """Soft delete tim beserta keanggotaannya."""
        await self.execute(
            "UPDATE member SET is_active = FALSE, delete_at = now(), update_at = now() "
            "WHERE team_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(team_id)},
        )
        await self.execute(
            "UPDATE team SET status = FALSE, delete_at = now(), update_at = now() "
            "WHERE team_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(team_id)},
        )

    async def is_member(self, team_id: UUID | str, employee_id: UUID | str) -> bool:
        return bool(
            await self.scalar(
                "SELECT EXISTS (SELECT 1 FROM member WHERE team_id = CAST(:t AS uuid) "
                "AND employee_id = CAST(:e AS uuid) AND delete_at IS NULL AND is_active)",
                {"t": str(team_id), "e": str(employee_id)},
            )
        )

    async def add_member(self, team_id: UUID | str, employee_id: UUID | str) -> None:
        """Satu baris member per (tim, karyawan): baris lama yang keluar dihidupkan lagi, bukan diduplikasi."""
        revived = await self.scalar(
            """
            UPDATE member SET is_active = TRUE, delete_at = NULL, update_at = now()
            WHERE member_id = (
                SELECT member_id FROM member
                WHERE team_id = CAST(:t AS uuid) AND employee_id = CAST(:e AS uuid)
                ORDER BY create_at DESC LIMIT 1
            )
            RETURNING member_id
            """,
            {"t": str(team_id), "e": str(employee_id)},
        )
        if revived is None:
            await self.execute(
                "INSERT INTO member (team_id, employee_id) VALUES (CAST(:t AS uuid), CAST(:e AS uuid))",
                {"t": str(team_id), "e": str(employee_id)},
            )

    async def remove_member(self, team_id: UUID | str, employee_id: UUID | str) -> bool:
        removed = await self.scalar(
            """
            UPDATE member SET is_active = FALSE, delete_at = now(), update_at = now()
            WHERE team_id = CAST(:t AS uuid) AND employee_id = CAST(:e AS uuid) AND delete_at IS NULL
            RETURNING member_id
            """,
            {"t": str(team_id), "e": str(employee_id)},
        )
        return removed is not None
