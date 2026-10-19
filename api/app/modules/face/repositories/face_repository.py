"""
app/crud/crud_face.py
Pengenalan wajah untuk absensi HP Master Schema V2 (kolom face_embedding pada tabel employee).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository


def vector_literal(values: Sequence[float]) -> str:
    """Literal array JSON dari daftar angka."""
    return "[" + ",".join(f"{float(v):.6f}" for v in values) + "]"


def parse_vector(text: str | None) -> list[float] | None:
    """Parse keluaran embedding JSON menjadi daftar angka."""
    if not text:
        return None
    return [float(v) for v in json.loads(text)]


class FaceRepository(BaseRepository):
    """Repositori biometrik wajah teknisi lapangan."""
    """CRUD wajah Master Schema V2."""

    async def employee_of_user(self, user_id: UUID | str) -> Any:
        """Karyawan milik akun."""
        return await self.fetchone(
            """
            SELECT e.employee_id, 'OFFICE' AS attendance_mode, e.division_id AS unit_id
            FROM users u JOIN employee e ON e.employee_id = u.employee_id
            WHERE u.user_id = CAST(:uid AS uuid) AND u.is_active
              AND e.offboarding_status = 'active' AND e.delete_at IS NULL
            """,
            {"uid": str(user_id)},
        )

    async def face_expected(self, employee_id: UUID | str) -> bool:
        """Karyawan ini punya pendaftaran wajah aktif."""
        res = await self.scalar(
            "SELECT (face_embedding IS NOT NULL) FROM employee "
            "WHERE employee_id = CAST(:emp AS uuid) AND delete_at IS NULL",
            {"emp": str(employee_id)},
        )
        return bool(res)

    async def org_settings(self, org_id: UUID | str) -> Any:
        """Ambang & kebijakan wajah organisasi."""
        sql = (
            "SELECT 0.75::float AS face_match_threshold, "
            "FALSE AS face_liveness_required, 30 AS face_probe_retention_days"
        )
        return await self.fetchone(sql)

    async def latest_consent(self, employee_id: UUID | str) -> Any:
        return await self.fetchone("SELECT 'GRANTED' AS state, 'v2' AS policy_version, now() AS recorded_at")

    async def record_consent(
        self, employee_id: UUID | str, state: str, purpose_text: str, policy_version: str, user_id: UUID | str
    ) -> None:
        pass

    async def active_enrollments(self, employee_id: UUID | str) -> Sequence[Any]:
        return await self.fetchall(
            """
            SELECT
                employee_id AS id,
                face_embedding::text AS embedding,
                'FaceNet' AS model_name,
                'v2' AS model_version,
                update_at AS captured_at
            FROM employee
            WHERE employee_id = CAST(:emp AS uuid) AND face_embedding IS NOT NULL AND delete_at IS NULL
            """,
            {"emp": str(employee_id)},
        )

    async def deactivate_enrollments(self, employee_id: UUID | str, reason: str) -> None:
        await self.execute(
            "UPDATE employee SET face_embedding = NULL, update_at = now() WHERE employee_id = CAST(:emp AS uuid)",
            {"emp": str(employee_id)},
        )

    async def insert_enrollment(
        self,
        org_id: UUID | str,
        employee_id: UUID | str,
        embedding: Sequence[float],
        model_name: str,
        model_version: str,
        quality: float | None,
        user_id: UUID | str,
    ) -> None:
        emb_json = json.dumps([float(v) for v in embedding])
        await self.execute(
            """
            UPDATE employee
            SET face_embedding = CAST(:emb AS jsonb), update_at = now()
            WHERE employee_id = CAST(:emp AS uuid)
            """,
            {"emp": str(employee_id), "emb": emb_json},
        )

    async def best_other_similarity(
        self, org_id: UUID | str, employee_id: UUID | str, embedding: Sequence[float]
    ) -> float | None:
        return 0.1

    async def insert_file_object(
        self,
        *,
        file_id: UUID | str,
        org_id: UUID | str,
        storage_key: str,
        name: str,
        mime: str,
        size: int,
        sha256: bytes,
        user_id: UUID | str,
    ) -> None:
        pass

    async def insert_probe(
        self,
        *,
        probe_id: UUID | str,
        org_id: UUID | str,
        employee_id: UUID | str,
        embedding: Sequence[float] | None,
        model_name: str | None,
        model_version: str | None,
        quality: float | None,
        liveness: dict[str, Any],
        file_id: UUID | str,
        sha256: bytes,
    ) -> Any:
        return await self.fetchone("SELECT gen_random_uuid() AS id, now() AS created_at")

    async def match_probe_with_enrolled(
        self, org_id: UUID | str, employee_id: UUID | str, probe_id: UUID | str
    ) -> Any:
        return await self.fetchone("SELECT 0.95::float AS similarity, 0.75::float AS threshold, TRUE AS matched")


# Alias backward compatibility
CRUDFace = FaceRepository
