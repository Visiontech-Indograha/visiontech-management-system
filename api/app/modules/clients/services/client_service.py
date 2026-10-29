"""
Klien (Milestone 10): pengelola rencana (`create:plan`: PM/OM/SUPER_ADMIN) mengelola; semua yang login membaca.
Kode klien unik; klien yang sudah punya proyek tidak bisa dihapus (nonaktifkan lewat `status`).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.security import CurrentUser
from app.modules.clients.repositories.client_repository import ClientRepository
from app.modules.clients.schemas.client_schema import ClientCreate, ClientUpdate
from app.shared.access.access_service import is_admin

CODE_TAKEN = "Kode klien sudah dipakai."


class ClientService:
    def __init__(self, repo: ClientRepository) -> None:
        self.repo = repo

    async def list(self, q: str | None, active_only: bool) -> list[Any]:
        return await self.repo.list((q or "").strip() or None, active_only)

    async def get(self, client_id: UUID) -> Any:
        row = await self.repo.get(client_id)
        if row is None:
            raise NotFoundError("Klien")
        return row

    async def create(self, data: ClientCreate) -> Any:
        code = data.client_code.strip().upper()
        if await self.repo.code_taken(code):
            raise AppError("CLIENT_CODE_TAKEN", CODE_TAKEN, status=409)
        return await self.repo.insert({**data.model_dump(), "client_code": code, "name": data.name.strip()})

    async def _check_manage(self, client_id: UUID, user: CurrentUser) -> None:
        """Klien yang sudah punya proyek hanya diubah/dihapus PM/OM divisi pemilik proyek (atau SUPER_ADMIN)."""
        row = await self.get(client_id)
        if is_admin(user) or not row.project_count:
            return
        if not await self.repo.manages_via_project(client_id, user.employee_id):
            raise ForbiddenError("Klien ini punya proyek di divisi lain; hanya PM/OM divisi itu yang mengubahnya.")

    async def update(self, client_id: UUID, data: ClientUpdate, user: CurrentUser) -> Any:
        await self._check_manage(client_id, user)
        fields = data.model_dump(exclude_unset=True)
        if fields.get("client_code"):
            fields["client_code"] = fields["client_code"].strip().upper()
            if await self.repo.code_taken(fields["client_code"], exclude=client_id):
                raise AppError("CLIENT_CODE_TAKEN", CODE_TAKEN, status=409)
        return await self.repo.update(client_id, fields)

    async def delete(self, client_id: UUID, user: CurrentUser) -> None:
        await self._check_manage(client_id, user)
        row = await self.get(client_id)
        if row.project_count:
            raise AppError("CLIENT_IN_USE", f"Klien masih punya {row.project_count} proyek. Nonaktifkan saja.",
                           status=409)
        await self.repo.archive(client_id)
