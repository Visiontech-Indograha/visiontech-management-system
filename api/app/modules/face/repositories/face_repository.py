"""
app/modules/face/repositories/face_repository.py
Wajah V2: `employee.face_embedding` (jsonb) menyimpan vektor pendaftaran + metadata model.
Bentuk tersimpan: {"vector": [...], "model": "...", "version": "...", "enrolled_at": "..."}; data seed lama berupa
larik angka murni tetap terbaca.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository


def parse_embedding(raw: Any) -> tuple[list[float] | None, dict[str, Any]]:
    """(vektor, metadata) dari nilai jsonb face_embedding."""
    if raw is None:
        return None, {}
    data = json.loads(raw) if isinstance(raw, str) else raw
    if isinstance(data, list):
        return [float(v) for v in data], {}
    if isinstance(data, dict) and isinstance(data.get("vector"), list):
        return [float(v) for v in data["vector"]], {k: v for k, v in data.items() if k != "vector"}
    return None, {}


class FaceRepository(BaseRepository):
    """Query wajah pada tabel employee."""

    async def employee_of_user(self, user_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT e.employee_id, u.system_role::text AS role, e.face_embedding
            FROM users u JOIN employee e ON e.employee_id = u.employee_id
            WHERE u.user_id = CAST(:uid AS uuid) AND u.is_active AND u.delete_at IS NULL
              AND e.offboarding_status = 'active' AND e.delete_at IS NULL
            """,
            {"uid": str(user_id)},
        )

    async def employee_face_row(self, employee_id: UUID | str) -> Any:
        """Karyawan (belum dihapus) beserta peran akunnya dan wajah terdaftar; untuk status oleh HR/admin."""
        return await self.fetchone(
            """
            SELECT e.employee_id, u.system_role::text AS role, e.face_embedding
            FROM employee e
            LEFT JOIN users u ON u.employee_id = e.employee_id AND u.delete_at IS NULL
            WHERE e.employee_id = CAST(:emp AS uuid) AND e.delete_at IS NULL
            """,
            {"emp": str(employee_id)},
        )

    async def embedding_of(self, employee_id: UUID | str) -> Any:
        return await self.scalar(
            "SELECT face_embedding FROM employee WHERE employee_id = CAST(:emp AS uuid) AND delete_at IS NULL",
            {"emp": str(employee_id)},
        )

    async def other_embeddings(self, employee_id: UUID | str) -> list[Any]:
        """Wajah terdaftar karyawan aktif lain — mencegah satu wajah didaftarkan untuk dua akun."""
        return list(await self.fetchall(
            "SELECT employee_id, face_embedding FROM employee WHERE face_embedding IS NOT NULL "
            "AND employee_id <> CAST(:emp AS uuid) AND delete_at IS NULL AND offboarding_status = 'active'",
            {"emp": str(employee_id)},
        ))

    async def set_embedding(self, employee_id: UUID | str, vector: list[float], model: str, version: str,
                            enrolled_at: datetime) -> None:
        payload = {"vector": [round(float(v), 6) for v in vector], "model": model, "version": version,
                   "enrolled_at": enrolled_at.isoformat()}
        await self.execute(
            "UPDATE employee SET face_embedding = CAST(:emb AS jsonb), update_at = now() "
            "WHERE employee_id = CAST(:emp AS uuid)",
            {"emp": str(employee_id), "emb": json.dumps(payload)},
        )

    async def clear_embedding(self, employee_id: UUID | str) -> bool:
        cleared = await self.scalar(
            "UPDATE employee SET face_embedding = NULL, update_at = now() "
            "WHERE employee_id = CAST(:emp AS uuid) AND delete_at IS NULL RETURNING employee_id",
            {"emp": str(employee_id)},
        )
        return cleared is not None

    async def self_reset_within_day(self, employee_id: UUID | str) -> bool:
        """Apakah karyawan ini sudah menghapus wajahnya sendiri dalam 24 jam terakhir."""
        found = await self.scalar(
            "SELECT 1 FROM public.app_activity_logs "
            "WHERE action = 'FACE_SELF_RESET' AND entity_id = CAST(:emp AS uuid) "
            "AND created_at >= now() - interval '1 day' LIMIT 1",
            {"emp": str(employee_id)},
        )
        return found is not None

    async def file_key(self, file_id: UUID | str) -> str | None:
        key: str | None = await self.scalar(
            "SELECT storage_key FROM file_object WHERE id = CAST(:id AS uuid)", {"id": str(file_id)}
        )
        return key
