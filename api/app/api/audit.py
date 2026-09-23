from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.api.deps import CurrentUser, get_db_with_user, require_permission
from app.core.permissions import Permission
from app.schemas.audit import AuditEventListResponse, AuditEventResponse

router = APIRouter(prefix="/audit-events", tags=["Audit"])

@router.get("", response_model=AuditEventListResponse)
async def get_audit_events(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    entity_type: str = None,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_AUDIT)),
    db: AsyncSession = Depends(get_db_with_user)
):
    """
    Mengambil daftar kejadian audit. Hanya dapat diakses oleh Admin atau peran dengan VIEW_REPORTS.
    Data difilter otomatis berdasarkan organization_id lewat RLS jika diatur.
    """
    offset = (page - 1) * size
    
    # Base query components
    where_clause = ""
    params = {"limit": size, "offset": offset}
    
    if entity_type:
        where_clause = "WHERE entity_type = :entity_type"
        params["entity_type"] = entity_type
        
    count_query = text(f"SELECT COUNT(*) FROM vms.audit_event {where_clause}")
    total_result = await db.execute(count_query, params)
    total = total_result.scalar() or 0
    
    query = text(f"""
        SELECT id, occurred_at, actor_label, action, entity_type, entity_id, detail, changes
        FROM vms.audit_event
        {where_clause}
        ORDER BY occurred_at DESC
        LIMIT :limit OFFSET :offset
    """)
    result = await db.execute(query, params)
    rows = result.fetchall()
    
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
