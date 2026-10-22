"""
app/modules/audit/routes/audit_route.py

Rute endpoint HTTP untuk riwayat kejadian audit (/audit-events).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from typing import Any

from fastapi import APIRouter, Depends, Query

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
    entity_type: str | None = None,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_AUDIT)),
    controller: AuditController = Depends(),
) -> AuditEventListResponse:
    """Mendapatkan daftar kejadian audit organisasi pengguna."""
    return await controller.handle_list_events(current_user, page, size, entity_type)
