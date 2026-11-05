"""
app/modules/audit/routes/audit_route.py

Rute endpoint HTTP untuk riwayat kejadian audit (/audit-events).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import require_permission
from app.core.keyset import cursor_query, finish_page, parse_cursor
from app.core.list_params import check_date_range
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.audit.controllers.audit_controller import AuditController
from app.modules.audit.schemas.audit_schema import AuditEventListResponse, AuditEventResponse

router = APIRouter(prefix="/audit-events", tags=["Audit"])


@router.get("/backups")
async def get_system_backups(
    # Sama dengan /backup-registry: lokasi berkas (bucket) & checksum hanya untuk pengelola backup (SA).
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_BACKUPS)),
    controller: AuditController = Depends(),
) -> list[dict[str, Any]]:
    """Mendapatkan daftar berkas arsip backup sistem dari public.system_backup_registry."""
    return await controller.handle_list_backups()


@router.get("", response_model=AuditEventListResponse)
async def get_audit_events(
    response: Response,
    cursor: str | None = cursor_query(),
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
    check_date_range(date_from, date_to)
    after = parse_cursor(cursor, ("datetime", "uuid"))
    if after is not None:
        # Mode keyset: tanpa COUNT; `total` = 0, `page` = 1; lanjutan lewat header X-Next-Cursor.
        rows = await controller.handle_list_events_keyset(
            current_user, size, entity_type, after, (q or "").strip() or None, date_from, date_to
        )
        items: list[AuditEventResponse] = finish_page(rows, size, response, lambda r: (r.occurred_at, r.id))
        return AuditEventListResponse(items=items, total=0, page=1, size=size)
    return await controller.handle_list_events(
        current_user, page, size, entity_type, (q or "").strip() or None, date_from, date_to
    )
