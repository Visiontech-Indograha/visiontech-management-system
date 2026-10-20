"""
app/modules/teams/repositories/team_repository.py
Repository akses basis data untuk tabel team dan member (Master Schema V2).
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.core.repository import CRUDBase
from app.modules.teams.schemas.team_schema import TeamCreate, TeamUpdate


class TeamRepository(CRUDBase):
    """Akses query untuk entitas tim lapangan dan anggotanya."""

    async def list_teams(self, division_id: UUID | None = None) -> Sequence[Any]:
        """Mengambil daftar tim yang aktif dan belum dihapus."""
        sql = """
            SELECT
                t.team_id,
                t.office_id,
                t.division_id,
                t.leader_employee_id,
                t.name,
                t.status,
                t.create_at,
                e.full_name AS leader_name,
                d.name AS division_name,
                o.name AS office_name,
                (
                    SELECT COUNT(*)::int FROM member m
                    WHERE m.team_id = t.team_id AND m.delete_at IS NULL AND m.is_active = true
                ) AS member_count
            FROM team t
            LEFT JOIN employee e ON e.employee_id = t.leader_employee_id
            LEFT JOIN division d ON d.division_id = t.division_id
            LEFT JOIN office o ON o.office_id = t.office_id
            WHERE t.delete_at IS NULL
        """
        params: dict[str, Any] = {}
        if division_id:
            sql += " AND t.division_id = :div_id"
            params["div_id"] = division_id
        sql += " ORDER BY t.name ASC"
        return await self.fetchall(sql, params)

    async def get_team_by_id(self, team_id: UUID) -> Any | None:
        """Mengambil data tim berdasarkan ID."""
        sql = """
            SELECT
                t.team_id,
                t.office_id,
                t.division_id,
                t.leader_employee_id,
                t.name,
                t.status,
                t.create_at,
                e.full_name AS leader_name,
                d.name AS division_name,
                o.name AS office_name,
                (
                    SELECT COUNT(*)::int FROM member m
                    WHERE m.team_id = t.team_id AND m.delete_at IS NULL AND m.is_active = true
                ) AS member_count
            FROM team t
            LEFT JOIN employee e ON e.employee_id = t.leader_employee_id
            LEFT JOIN division d ON d.division_id = t.division_id
            LEFT JOIN office o ON o.office_id = t.office_id
            WHERE t.team_id = :team_id AND t.delete_at IS NULL
        """
        return await self.fetchone(sql, {"team_id": team_id})

    async def list_team_members(self, team_id: UUID) -> Sequence[Any]:
        """Mengambil daftar anggota suatu tim."""
        sql = """
            SELECT
                m.member_id,
                m.team_id,
                m.employee_id,
                m.is_active,
                m.create_at,
                e.full_name,
                e.employee_no
            FROM member m
            JOIN employee e ON e.employee_id = m.employee_id
            WHERE m.team_id = :team_id AND m.delete_at IS NULL
            ORDER BY e.full_name ASC
        """
        return await self.fetchall(sql, {"team_id": team_id})

    async def create_team(self, data: TeamCreate) -> Any:
        """Menyisipkan record tim baru ke tabel team."""
        team_id = uuid.uuid4()
        sql = """
            INSERT INTO team (
                team_id, office_id, division_id, leader_employee_id, name, status,
                create_at, update_at
            ) VALUES (
                :team_id, :office_id, :division_id, :leader_id, :name, :status,
                NOW(), NOW()
            )
            RETURNING team_id, office_id, division_id, leader_employee_id, name, status, create_at
        """
        return await self.fetchone(sql, {
            "team_id": team_id,
            "office_id": data.office_id,
            "division_id": data.division_id,
            "leader_id": data.leader_employee_id,
            "name": data.name,
            "status": data.status,
        })

    async def update_team(self, team_id: UUID, data: TeamUpdate) -> Any | None:
        """Memperbarui data tim."""
        updates: list[str] = ["update_at = NOW()"]
        params: dict[str, Any] = {"team_id": team_id}
        if data.office_id is not None:
            updates.append("office_id = :office_id")
            params["office_id"] = data.office_id
        if data.division_id is not None:
            updates.append("division_id = :division_id")
            params["division_id"] = data.division_id
        if data.leader_employee_id is not None:
            updates.append("leader_employee_id = :leader_id")
            params["leader_id"] = data.leader_employee_id
        if data.name is not None:
            updates.append("name = :name")
            params["name"] = data.name
        if data.status is not None:
            updates.append("status = :status")
            params["status"] = data.status

        sql = f"UPDATE team SET {', '.join(updates)} WHERE team_id = :team_id AND delete_at IS NULL"
        await self.execute(sql, params)
        return await self.get_team_by_id(team_id)

    async def delete_team(self, team_id: UUID) -> bool:
        """Soft delete tim kerja."""
        sql = "UPDATE team SET delete_at = NOW(), status = false WHERE team_id = :team_id AND delete_at IS NULL"
        await self.execute(sql, {"team_id": team_id})
        return True

    async def add_member(self, team_id: UUID, employee_id: UUID) -> Any:
        """Menambahkan anggota ke tim."""
        # Cek apakah sudah pernah ada record member sebelumnya (mungkin nonaktif)
        check_sql = "SELECT member_id FROM member WHERE team_id = :team_id AND employee_id = :emp_id"
        existing = await self.fetchone(check_sql, {"team_id": team_id, "emp_id": employee_id})
        if existing:
            update_sql = """
                UPDATE member SET is_active = true, delete_at = NULL, update_at = NOW()
                WHERE member_id = :member_id
                RETURNING member_id, team_id, employee_id, is_active, create_at
            """
            return await self.fetchone(update_sql, {"member_id": existing.member_id})

        member_id = uuid.uuid4()
        insert_sql = """
            INSERT INTO member (member_id, team_id, employee_id, is_active, create_at, update_at)
            VALUES (:member_id, :team_id, :emp_id, true, NOW(), NOW())
            RETURNING member_id, team_id, employee_id, is_active, create_at
        """
        return await self.fetchone(insert_sql, {
            "member_id": member_id,
            "team_id": team_id,
            "emp_id": employee_id,
        })

    async def remove_member(self, team_id: UUID, employee_id: UUID) -> bool:
        """Menonaktifkan / mengeluarkan anggota dari tim."""
        sql = """
            UPDATE member SET is_active = false, delete_at = NOW(), update_at = NOW()
            WHERE team_id = :team_id AND employee_id = :emp_id AND delete_at IS NULL
        """
        await self.execute(sql, {"team_id": team_id, "emp_id": employee_id})
        return True
