"""
app/crud/crud_sync.py
Antrean offline dan sinkronisasi Master Schema V2 (tabel app_activity_logs).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository


class SyncRepository(BaseRepository):
    """Repositori sinkronisasi data offline mobile."""
    """
    CRUD untuk mengelola antrean operasi offline Master Schema V2.
    """

    async def enqueue(
        self,
        org_id: UUID | str,
        user_id: UUID | str,
        device_id: str,
        client_op_id: UUID,
        op_type: str,
        payload: dict[str, Any],
        client_created_at: datetime,
    ) -> Any:
        """
        Mencatat operasi offline ke antrean (app_activity_logs). Idempoten per (pengguna, client_op_id): kiriman
        ulang mengembalikan hasil sebelumnya; operasi baru berstatus PENDING agar service menjalankannya.
        """
        existing = await self.fetchone(
            """
            SELECT log_id AS id, COALESCE(changed_diff->>'status', 'PENDING') AS status,
                   NULLIF(changed_diff->>'error_message', '') AS error_message
            FROM app_activity_logs
            WHERE actor_user_id = CAST(:user AS uuid) AND action = 'OFFLINE_OPERATION'
              AND changed_diff->>'client_op_id' = CAST(:op AS text)
            ORDER BY created_at
            LIMIT 1
            """,
            {"user": str(user_id), "op": str(client_op_id)},
        )
        if existing is not None:
            return existing
        row = await self.fetchone(
            """
            INSERT INTO app_activity_logs (
                actor_user_id, actor_role, platform, action,
                entity_table, entity_id, changed_diff, created_at
            )
            VALUES (
                CAST(:user AS uuid), 'EMPLOYEE', 'android_flutter',
                'OFFLINE_OPERATION', 'offline_sync', CAST(:op AS uuid),
                jsonb_build_object(
                    'client_op_id', CAST(:op AS text),
                    'op_type', CAST(:type AS text),
                    'status', 'PENDING',
                    'device_id', CAST(:device AS text),
                    'payload', CAST(:payload AS jsonb),
                    'client_created_at', CAST(:created AS text)
                ),
                NOW()
            )
            RETURNING log_id AS id, 'PENDING' AS status, NULL AS error_message
            """,
            {
                "user": str(user_id),
                "device": device_id,
                "op": str(client_op_id),
                "type": op_type,
                "payload": json.dumps(payload),
                "created": client_created_at.isoformat(),
            },
        )
        return row

    async def mark(self, operation_id: UUID | str, status: str, error_message: str | None) -> None:
        """Menandai status akhir dari operasi offline."""
        await self.execute(
            """
            UPDATE app_activity_logs
            SET changed_diff = jsonb_set(
                jsonb_set(changed_diff, '{status}', to_jsonb(CAST(:status AS text))),
                '{error_message}', to_jsonb(CAST(:error AS text))
            )
            WHERE log_id = CAST(:id AS uuid)
            """,
            {"id": str(operation_id), "status": status, "error": error_message or ""},
        )

    async def status_since(self, user_id: UUID | str, since: datetime | None) -> list[Any]:
        """Mengambil status operasi offline pengguna."""
        return list(
            await self.fetchall(
                """
            SELECT changed_diff->>'client_op_id' AS client_op_id,
                   changed_diff->>'op_type' AS op_type,
                   COALESCE(changed_diff->>'status', 'APPLIED') AS status,
                   changed_diff->>'error_message' AS error_message,
                   created_at AS client_created_at,
                   created_at AS received_at,
                   created_at AS applied_at
            FROM app_activity_logs
            WHERE actor_user_id = CAST(:user AS uuid)
              AND action = 'OFFLINE_OPERATION'
              AND (CAST(:since AS timestamptz) IS NULL OR created_at >= CAST(:since AS timestamptz))
            ORDER BY created_at DESC
            LIMIT 500
            """,
                {"user": str(user_id), "since": since},
            )
        )


CRUDSync = SyncRepository
