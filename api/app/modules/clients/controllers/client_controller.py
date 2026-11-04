"""Controller klien."""
from __future__ import annotations

from datetime import date  # noqa: F401
from typing import Any  # noqa: F401
from uuid import UUID

from fastapi import Depends

from app.core.errors import ForbiddenError
from app.core.security import CurrentUser
from app.modules.clients.dependencies import get_client_service
from app.modules.clients.schemas.client_schema import (
    ClientCreate,
    ClientOut,
    ClientSiteCreate,
    ClientSiteOut,
    ClientSiteUpdate,
    ClientUpdate,
)
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
    async def list_sites(self, user: CurrentUser, client_id: UUID) -> list[ClientSiteOut]:
        if not can_read_clients(user):
            raise ForbiddenError("Daftar lokasi klien hanya untuk pengelola tugas dan PM.")
        rows = await self.service.list_sites(client_id)
        return [ClientSiteOut(**dict(r._mapping)) for r in rows]

    async def create_site(self, user: CurrentUser, client_id: UUID, data: ClientSiteCreate) -> ClientSiteOut:
        row = await self.service.create_site(client_id, data, user)
        return ClientSiteOut(**dict(row._mapping))

    async def update_site(
        self, user: CurrentUser, client_id: UUID, site_id: UUID, data: ClientSiteUpdate
    ) -> ClientSiteOut:
        row = await self.service.update_site(client_id, site_id, data, user)
        return ClientSiteOut(**dict(row._mapping))

    async def delete_site(self, user: CurrentUser, client_id: UUID, site_id: UUID) -> dict[str, str]:
        await self.service.delete_site(client_id, site_id, user)
        return {"message": "Lokasi klien berhasil dihapus."}

