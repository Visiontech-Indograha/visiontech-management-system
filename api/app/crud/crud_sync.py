"""
app/crud/crud_sync.py
Antrean luring (M12, dok 02 A-08): offline_operation + enqueue_offline_operation (db/01, db/02).
Idempoten per (user_id, client_op_id).
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDSync(CRUDBase):

    async def enqueue(self, org_id: UUID | str, user_id: UUID | str, device_id: str, client_op_id: UUID,
                      op_type: str, payload: dict[str, Any], client_created_at: datetime) -> Any:
        """Catat (atau temukan) operasi; kembalikan baris beserta status saat ini."""
        # Dua pernyataan: baris hasil INSERT di dalam fungsi tak terlihat oleh snapshot SELECT yang sama.
        enqueued = await self.fetchone(
            """
            SELECT vms.enqueue_offline_operation(
                CAST(:org AS uuid), CAST(:user AS uuid), :device, CAST(:op AS uuid), :type,
                CAST(:payload AS jsonb), CAST(:created AS timestamptz)) AS id
            """,
            {"org": org_id, "user": user_id, "device": device_id, "op": client_op_id, "type": op_type,
             "payload": json.dumps(payload), "created": client_created_at})
        return await self.fetchone(
            """
            SELECT o.id, CAST(o.status AS text) AS status, o.error_message
            FROM vms.offline_operation o
            WHERE o.id = CAST(:id AS uuid)
            """,
            {"id": enqueued.id})

    async def mark(self, operation_id: UUID | str, status: str, error_message: str | None) -> None:
        await self.execute(
            """
            UPDATE vms.offline_operation
               SET status = CAST(:status AS vms.sync_status), error_message = :error,
                   applied_at = CASE WHEN CAST(:status AS text) = 'APPLIED' THEN now() ELSE applied_at END
             WHERE id = :id
            """,
            {"id": operation_id, "status": status, "error": error_message})

    async def status_since(self, user_id: UUID | str, since: datetime | None) -> list[Any]:
        return list(await self.fetchall(
            """
            SELECT CAST(client_op_id AS text) AS client_op_id, op_type, CAST(status AS text) AS status,
                   error_message, client_created_at, received_at, applied_at
            FROM vms.offline_operation
            WHERE user_id = :user
              AND (CAST(:since AS timestamptz) IS NULL OR received_at >= CAST(:since AS timestamptz))
            ORDER BY received_at DESC
            LIMIT 500
            """,
            {"user": user_id, "since": since}))
