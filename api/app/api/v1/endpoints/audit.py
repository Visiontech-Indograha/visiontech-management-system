"""
Modul endpoint untuk fitur Audit.
Menangani pengambilan riwayat kejadian (audit events) dalam sistem.
"""
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_audit_service, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.schemas.audit import AuditEventListResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-events", tags=["Audit"])

@router.get("", response_model=AuditEventListResponse)
async def get_audit_events(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    entity_type: str | None = None,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_AUDIT)),
    service: AuditService = Depends(get_audit_service),
) -> AuditEventListResponse:
    """
    Mendapatkan daftar kejadian audit organisasi pengguna (VIEW_AUDIT).
    Disaring `organization_id` secara eksplisit — tidak hanya mengandalkan RLS,
    yang terlewati bila aplikasi terhubung sebagai pemilik tabel (T-12).

    Query params:
    - page: Nomor halaman (default 1)
    - size: Jumlah item per halaman (default 20, max 100)
    - entity_type: Filter opsional berdasarkan jenis entitas (contoh: "User", "Asset")

    Return: Daftar riwayat audit beserta pagination (AuditEventListResponse)
    """
    return await service.list_events(current_user.organization_id, page, size, entity_type)
