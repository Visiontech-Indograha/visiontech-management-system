"""
app/services/audit_service.py
Daftar riwayat audit organisasi pengguna (VIEW_AUDIT) dengan pagination.
"""
from __future__ import annotations

from uuid import UUID

from app.crud.crud_audit import CRUDAudit
from app.schemas.audit import AuditEventListResponse, AuditEventResponse


class AuditService:
    """Layanan baca audit; penulisan audit dilakukan trigger basis data."""

    def __init__(self, repo: CRUDAudit) -> None:
        self.repo = repo

    async def list_events(self, org_id: UUID | str, page: int, size: int,
                          entity_type: str | None) -> AuditEventListResponse:
        """Halaman `page` (mulai 1) berisi `size` kejadian, terbaru lebih dulu."""
        total = await self.repo.count(org_id, entity_type)
        rows = await self.repo.list_page(org_id, entity_type, size, (page - 1) * size)
        items = [AuditEventResponse(
            id=r.id, occurred_at=r.occurred_at, actor_label=r.actor_label, action=r.action,
            entity_type=r.entity_type, entity_id=r.entity_id, detail=r.detail, changes=r.changes,
        ) for r in rows]
        return AuditEventListResponse(items=items, total=total, page=page, size=size)
