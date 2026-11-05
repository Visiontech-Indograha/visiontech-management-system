"""
app/modules/audit/controllers/audit_controller.py

Controller orkestrasi use case penelusuran riwayat log audit.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.audit.dependencies import get_audit_service
from app.modules.audit.schemas.audit_schema import AuditEventListResponse, AuditEventResponse
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
        q: str | None = None,
        date_from: Any = None,
        date_to: Any = None,
    ) -> AuditEventListResponse:
        """Mengambil daftar kejadian audit organisasi pengguna dengan paginasi dan filter entitas."""
        return await self.service.list_events(
            current_user.organization_id, page, size, entity_type, q, date_from, date_to
        )

    async def handle_list_events_keyset(
        self,
        current_user: CurrentUser,
        size: int,
        entity_type: str | None,
        after: tuple[Any, ...],
        q: str | None = None,
        date_from: Any = None,
        date_to: Any = None,
    ) -> list[AuditEventResponse]:
        """Halaman keyset audit (size+1 baris)."""
        return await self.service.list_events_keyset(
            current_user.organization_id, size, entity_type, after, q, date_from, date_to
        )

    async def handle_list_backups(self) -> list[dict[str, Any]]:
        """Mengambil daftar berkas arsip backup sistem dari system_backup_registry."""
        return await self.service.list_backups()
