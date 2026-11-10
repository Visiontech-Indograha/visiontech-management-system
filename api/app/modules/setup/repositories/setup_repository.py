"""SQL penyiapan awal. Tidak commit (transaksi di service/get_db)."""
from __future__ import annotations

import uuid
from typing import Any

from app.core.repository import BaseRepository

# Kunci advisory transaksi: serialisasi penyiapan antar-proses/antar-permintaan.
SETUP_LOCK_KEY = 7_410_001


class SetupRepository(BaseRepository):
    async def lock(self) -> None:
        await self.execute("SELECT pg_advisory_xact_lock(:k)", {"k": SETUP_LOCK_KEY})

    async def has_active_super_admin(self) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM users WHERE system_role = 'SUPER_ADMIN' "
            "AND is_active = true AND delete_at IS NULL)"
        ))

    async def email_taken(self, email: str) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM users WHERE (email = :e OR username = :e) AND delete_at IS NULL)",
            {"e": email},
        ))

    async def first_or_new_office(self) -> Any:
        office_id = await self.scalar("SELECT office_id FROM office WHERE delete_at IS NULL ORDER BY office_id LIMIT 1")
        if office_id:
            return office_id
        return await self.scalar(
            "INSERT INTO office (name, address, latitude, longitude) "
            "VALUES ('Kantor Utama', 'Jakarta', -6.2088, 106.8456) RETURNING office_id"
        )

    async def insert_admin(self, office_id: Any, full_name: str, email: str, password_hash: str) -> Any:
        emp_id = await self.scalar(
            "INSERT INTO employee (office_id, full_name, employee_no, join_date) "
            "VALUES (:off, :name, :no, now()) RETURNING employee_id",
            {"off": office_id, "name": full_name, "no": f"ADMIN-{uuid.uuid4().hex[:8].upper()}"},
        )
        return await self.scalar(
            "INSERT INTO users (employee_id, username, email, password_hash, system_role, is_active) "
            "VALUES (:emp, :email, :email, :ph, 'SUPER_ADMIN', true) RETURNING user_id",
            {"emp": emp_id, "email": email, "ph": password_hash},
        )
