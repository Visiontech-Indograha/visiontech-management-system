"""
app/modules/system/routes/sync_route.py

Rute endpoint HTTP untuk sinkronisasi luring (/sync).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""
from datetime import datetime

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.system.controllers.sync_controller import SyncController
from app.modules.system.schemas.system_schema import (
    OperationStatus,
    SyncRequest,
    SyncResponse,
)

router = APIRouter(prefix="/sync", tags=["Offline Sync"])


@router.post("/operations", response_model=SyncResponse)
async def sync_operations(
    data: SyncRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: SyncController = Depends(),
) -> SyncResponse:
    """Idempoten per client_op_id; dijalankan sesuai urutan kiriman perangkat (dok 04 §7)."""
    return await controller.handle_sync_operations(current_user, data)


@router.get("/status", response_model=list[OperationStatus])
async def sync_status(
    since: datetime | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    controller: SyncController = Depends(),
) -> list[OperationStatus]:
    """Operasi milik pengguna sendiri — dasar layar "Perlu perhatian" (REJECTED)."""
    return await controller.handle_sync_status(current_user, since)


__all__ = ["router"]

