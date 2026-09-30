"""Sinkronisasi luring (M12, dok 05 §3.12): kirim antrean perangkat & baca status (perlu perhatian)."""
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db_with_user
from app.services.sync_service import SyncService

router = APIRouter(prefix="/sync", tags=["Offline Sync"])


class OfflineOperation(BaseModel):
    client_op_id: UUID
    op_type: str
    payload: dict[str, Any]
    client_created_at: datetime


class SyncRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=200)
    operations: list[OfflineOperation] = Field(max_length=200)


class OperationResult(BaseModel):
    client_op_id: str
    status: str               # APPLIED | REJECTED | CONFLICT | PENDING
    error_message: str | None


class SyncResponse(BaseModel):
    results: list[OperationResult]


class OperationStatus(BaseModel):
    client_op_id: str
    op_type: str
    status: str
    error_message: str | None
    client_created_at: datetime
    received_at: datetime
    applied_at: datetime | None


@router.post("/operations", response_model=SyncResponse)
async def sync_operations(data: SyncRequest, current_user: CurrentUser = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db_with_user)) -> SyncResponse:
    """Idempoten per client_op_id; dijalankan sesuai urutan kiriman perangkat (dok 04 §7)."""
    results = await SyncService(db).apply_operations(current_user, data.device_id, data.operations)
    return SyncResponse(results=[OperationResult(**r) for r in results])


@router.get("/status", response_model=list[OperationStatus])
async def sync_status(since: datetime | None = None, current_user: CurrentUser = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db_with_user)) -> list[OperationStatus]:
    """Operasi milik pengguna sendiri — dasar layar "Perlu perhatian" (REJECTED)."""
    return [OperationStatus(**row._mapping) for row in await SyncService(db).status(current_user, since)]
