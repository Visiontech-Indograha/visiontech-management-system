"""
app/modules/system/controllers/sync_controller.py

Controller orkestrasi use case sinkronisasi luring (kirim antrean & periksa status).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import Depends

from app.api.deps import get_sync_service
from app.core.security import CurrentUser
from app.modules.system.schemas.system_schema import (
    OperationResult,
    OperationStatus,
    SyncRequest,
    SyncResponse,
)
from app.modules.system.services.system_service import SyncService


class SyncController:
    """Controller eksekusi antrean operasi dan pemantauan status sinkronisasi luring."""

    def __init__(
        self,
        sync_service: SyncService = Depends(get_sync_service),
    ) -> None:
        self.service = sync_service

    async def handle_sync_operations(
        self,
        current_user: CurrentUser,
        data: SyncRequest,
    ) -> SyncResponse:
        """Menerapkan antrean operasi dari perangkat klien secara idempoten."""
        results = await self.service.apply_operations(
            current_user, data.device_id, data.operations
        )
        return SyncResponse(results=[OperationResult(**r) for r in results])

    async def handle_sync_status(
        self,
        current_user: CurrentUser,
        since: datetime | None = None,
    ) -> list[OperationStatus]:
        """Mengambil riwayat status operasi milik pengguna sendiri."""
        rows = await self.service.status(current_user, since)
        return [OperationStatus(**row._mapping) for row in rows]


__all__ = ["SyncController"]

