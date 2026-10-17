"""
app/modules/system_backup/routes/backup_route.py
Rute API HTTP untuk pengelolaan registry backup sistem.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.system_backup.controllers.backup_controller import BackupController
from app.modules.system_backup.schemas.backup_schema import BackupCreate, BackupOut

router = APIRouter(prefix="/backup-registry", tags=["Backup Registry"])


@router.get("", response_model=list[BackupOut])
async def list_backups(
    limit: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    controller: BackupController = Depends(),
) -> list[BackupOut]:
    """Mengambil riwayat pencatatan backup basis data sistem."""
    return await controller.handle_list_backups(current_user, limit)


@router.get("/{backup_id}", response_model=BackupOut)
async def get_by_id(
    backup_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: BackupController = Depends(),
) -> BackupOut:
    """Mengambil detail rekaman backup sistem."""
    return await controller.handle_get_by_id(current_user, backup_id)


@router.post("", response_model=BackupOut, status_code=201)
async def record_backup(
    data: BackupCreate,
    current_user: CurrentUser = Depends(get_current_user),
    controller: BackupController = Depends(),
) -> BackupOut:
    """Mencatat rekaman eksekusi backup berkala baru."""
    return await controller.handle_record_backup(current_user, data)
