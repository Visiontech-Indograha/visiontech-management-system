"""
app/modules/audit/routes/audit_route.py

Rute endpoint HTTP untuk riwayat kejadian audit (/audit-events).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.audit.controllers.audit_controller import AuditController
from app.modules.audit.schemas.audit_schema import AuditEventListResponse

router = APIRouter(prefix="/audit-events", tags=["Audit"])


@router.get("/backups")
async def get_system_backups(
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_AUDIT)),
    controller: AuditController = Depends(),
) -> list[dict[str, Any]]:
    """Mendapatkan daftar berkas arsip backup sistem dari public.system_backup_registry."""
    return await controller.handle_list_backups()


@router.get("", response_model=AuditEventListResponse)
async def get_audit_events(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    entity_type: str | None = Query(None, max_length=60),
    q: str | None = Query(None, max_length=100, description="Awalan aksi, tabel, atau nama pelaku"),
    date_from: date | None = Query(None, description="Mulai tanggal (inklusif)"),
    date_to: date | None = Query(None, description="Sampai tanggal (inklusif)"),
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_AUDIT)),
    controller: AuditController = Depends(),
) -> AuditEventListResponse:
    """Mendapatkan daftar kejadian audit organisasi pengguna."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from tidak boleh setelah date_to")
    return await controller.handle_list_events(
        current_user, page, size, entity_type, (q or "").strip() or None, date_from, date_to
    )
