"""Controller klien."""
from __future__ import annotations

from datetime import date  # noqa: F401
from typing import Any  # noqa: F401
from uuid import UUID

from fastapi import Depends

from app.core.errors import ForbiddenError
from app.core.security import CurrentUser
from app.modules.clients.dependencies import get_client_service
from app.modules.clients.schemas.client_schema import ClientCreate, ClientOut, ClientUpdate
from app.modules.clients.services.client_service import ClientService, can_read_clients


class ClientController:
    def __init__(self, service: ClientService = Depends(get_client_service)) -> None:
        self.service = service

    async def list_all(self, user: CurrentUser, q: str | None, active_only: bool) -> list[ClientOut]:
        if not can_read_clients(user):
            raise ForbiddenError("Daftar klien hanya untuk pembuat jadwal, order, dan HR.")
        return [ClientOut(**dict(r._mapping)) for r in await self.service.list(q, active_only)]

    async def create(self, user: CurrentUser, data: ClientCreate) -> ClientOut:
        return ClientOut(**dict((await self.service.create(data))._mapping))

    async def update(self, user: CurrentUser, item_id: UUID, data: ClientUpdate) -> ClientOut:
        return ClientOut(**dict((await self.service.update(item_id, data, user))._mapping))

    async def delete(self, user: CurrentUser, item_id: UUID) -> dict[str, str]:
        await self.service.delete(item_id, user)
        return {"message": "Klien dihapus."}
