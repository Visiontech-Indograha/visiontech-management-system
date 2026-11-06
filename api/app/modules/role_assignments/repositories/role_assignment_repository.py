"""Repositori `user_role_assignment` (ADR 0002). Tidak commit; transaksi di service."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository
from app.shared.device_credential_repository import DeviceCredentialRepository

_COLS = """
    a.assignment_id, a.user_id, a.role::text AS role, a.office_id, o.name AS office_name,
    a.source, a.created_at
"""


class RoleAssignmentRepository(BaseRepository):
    async def lock_user(self, user_id: UUID | str) -> Any:
        """Kunci baris pengguna (FOR UPDATE) agar cek aturan lalu tulis tidak bisa balapan. None bila tidak ada."""
        return await self.fetchone(
            "SELECT user_id, system_role::text AS system_role, is_active FROM users "
            "WHERE user_id = CAST(:u AS uuid) AND delete_at IS NULL FOR UPDATE",
            {"u": str(user_id)},
        )

    async def user_exists(self, user_id: UUID | str) -> bool:
        return bool(
            await self.scalar(
                "SELECT EXISTS (SELECT 1 FROM users WHERE user_id = CAST(:u AS uuid) AND delete_at IS NULL)",
                {"u": str(user_id)},
            )
        )

    async def list_active(self, user_id: UUID | str) -> list[Any]:
        return list(
            await self.fetchall(
                f"SELECT {_COLS} FROM user_role_assignment a LEFT JOIN office o ON o.office_id = a.office_id "
                "WHERE a.user_id = CAST(:u AS uuid) AND a.delete_at IS NULL ORDER BY a.created_at, a.assignment_id",
                {"u": str(user_id)},
            )
        )

    async def get_active(self, user_id: UUID | str, assignment_id: UUID | str) -> Any:
        return await self.fetchone(
            f"SELECT {_COLS} FROM user_role_assignment a LEFT JOIN office o ON o.office_id = a.office_id "
            "WHERE a.assignment_id = CAST(:a AS uuid) AND a.user_id = CAST(:u AS uuid) AND a.delete_at IS NULL",
            {"a": str(assignment_id), "u": str(user_id)},
        )

    async def office_active(self, office_id: UUID | str) -> bool:
        return bool(
            await self.scalar(
                "SELECT EXISTS (SELECT 1 FROM office WHERE office_id = CAST(:o AS uuid) AND delete_at IS NULL)",
                {"o": str(office_id)},
            )
        )

    async def insert(self, user_id: UUID | str, role: str, office_id: UUID | str | None, actor: str) -> Any:
        return await self.fetchone(
            "INSERT INTO user_role_assignment (user_id, role, office_id, source, created_by) "
            "VALUES (CAST(:u AS uuid), CAST(:r AS system_role_enum), CAST(:o AS uuid), 'MANUAL', CAST(:c AS uuid)) "
            "RETURNING assignment_id",
            {"u": str(user_id), "r": role, "o": str(office_id) if office_id else None, "c": actor},
        )

    async def revoke(self, assignment_id: UUID | str, actor: str) -> int:
        """Soft delete bersyarat (delete_at IS NULL); mengembalikan jumlah baris terpengaruh."""
        result = await self.execute(
            "UPDATE user_role_assignment SET delete_at = now(), delete_by = CAST(:d AS uuid) "
            "WHERE assignment_id = CAST(:a AS uuid) AND delete_at IS NULL",
            {"a": str(assignment_id), "d": actor},
        )
        return int(result.rowcount)

    async def revoke_device_credentials(self, user_id: UUID | str) -> int:
        """Peran dicabut: kredensial perangkat (masuk sidik jari) akun ini dicabut; akun harus masuk ulang."""
        return await DeviceCredentialRepository(self.db).revoke_user(user_id, "ROLE_REVOKED")
