"""
app/modules/audit/controllers/audit_controller.py

Controller orkestrasi use case penelusuran riwayat log audit.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""
from __future__ import annotations

from fastapi import Depends

from app.api.deps import get_audit_service
from app.core.security import CurrentUser
from app.modules.audit.schemas.audit_schema import AuditEventListResponse
from app.modules.audit.services.audit_service import AuditService


class AuditController:
    """
    Controller use case riwayat log audit kejadian organisasi.
    """

    def __init__(self, audit_service: AuditService = Depends(get_audit_service)) -> None:
        self.service = audit_service

    async def handle_list_events(
        self,
        current_user: CurrentUser,
        page: int,
        size: int,
        entity_type: str | None,
    ) -> AuditEventListResponse:
        """Mengambil daftar kejadian audit organisasi pengguna dengan paginasi dan filter entitas."""
        return await self.service.list_events(current_user.organization_id, page, size, entity_type)

    async def handle_list_backups(self) -> list[dict[str, Any]]:
        """Mengambil daftar berkas arsip backup sistem dari system_backup_registry."""
        return await self.service.list_backups()

