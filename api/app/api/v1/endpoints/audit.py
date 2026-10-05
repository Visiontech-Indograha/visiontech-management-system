"""
Modul endpoint untuk fitur Audit.
Menangani pencatatan dan pengambilan riwayat kejadian (audit events) dalam sistem.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.schemas.audit import AuditEventListResponse, AuditEventResponse

router = APIRouter(prefix="/audit-events", tags=["Audit"])

@router.get("", response_model=AuditEventListResponse)
async def get_audit_events(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    entity_type: str | None = None,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_AUDIT)),
    db: AsyncSession = Depends(get_db_with_user)
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
    # Menggunakan injeksi dependensi untuk mendapatkan koneksi database dengan konteks user saat ini
    # Mendapatkan detail user saat ini dengan memeriksa izin VIEW_AUDIT
    # Melakukan query langsung ke database untuk mengambil data audit yang difilter sesuai dengan organisasi user
    params = {"org": current_user.organization_id, "entity_type": entity_type,
              "limit": size, "offset": (page - 1) * size}
    total = (await db.execute(text("""
        SELECT COUNT(*) FROM vms.audit_event
        WHERE organization_id = CAST(:org AS uuid)
          AND (CAST(:entity_type AS text) IS NULL OR entity_type = CAST(:entity_type AS text))
    """), params)).scalar() or 0
    rows = (await db.execute(text("""
        SELECT id, occurred_at, actor_label, action, entity_type, entity_id, detail, changes
        FROM vms.audit_event
        WHERE organization_id = CAST(:org AS uuid)
          AND (CAST(:entity_type AS text) IS NULL OR entity_type = CAST(:entity_type AS text))
        ORDER BY occurred_at DESC
        LIMIT :limit OFFSET :offset
    """), params)).fetchall()

    items = []
    for row in rows:
        items.append(AuditEventResponse(
            id=row.id,
            occurred_at=row.occurred_at,
            actor_label=row.actor_label,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            detail=row.detail,
            changes=row.changes
        ))
        
    return AuditEventListResponse(
        items=items,
        total=total,
        page=page,
        size=size
    )
