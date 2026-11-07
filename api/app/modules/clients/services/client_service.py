"""
Klien (Milestone 10): pengelola rencana (`create:plan`: PM/OM/SUPER_ADMIN) mengelola. Daftar klien dibaca pengelola
rencana dan PM/OM/HR (pembuat jadwal & order); pekerja lapangan dan ketua tim tidak melihat daftar (memuat PIC).
Kode klien unik; nama klien unik tanpa memperhatikan huruf besar/kecil dan spasi di ujung; klien yang sudah
punya proyek tidak bisa dihapus (nonaktifkan lewat `status`).
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.core.audit_log import record_audit
from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.clients.repositories.client_repository import ClientRepository
from app.modules.clients.schemas.client_schema import ClientCreate, ClientSiteCreate, ClientSiteUpdate, ClientUpdate
from app.shared.access.access_service import is_admin

CODE_TAKEN = "Kode klien sudah dipakai."
_LIST_ROLES = ("ADMIN_HR_GA", "OPERATIONAL_MANAGER", "PROJECT_MANAGER", "SUPER_ADMIN")


def can_read_clients(user: CurrentUser) -> bool:
    return Permission.CREATE_PLAN.value in user.permissions or user.has_role(*_LIST_ROLES)


_CLIENT_FIELDS = ("client_code", "name", "status")
_CLIENT_MASKED = ("pic_name", "pic_phone", "address")
_SITE_FIELDS = ("site_name", "latitude", "longitude", "geofence_radius_meters")
_SITE_MASKED = ("address", "pic_name", "pic_phone")


class ClientService:
    def __init__(self, repo: ClientRepository) -> None:
        self.repo = repo

    async def _audit(
        self, user: CurrentUser, action: str, entity_id: Any, before: Any, after: Any, *, site: bool = False,
        client_id: UUID | None = None, skip_if_empty: bool = False,
    ) -> None:
        await record_audit(
            self.repo.db, user, action=action, entity_type="client_sites" if site else "client",
            entity_id=entity_id, before=before, after=after,
            fields=_SITE_FIELDS if site else _CLIENT_FIELDS, masked=_SITE_MASKED if site else _CLIENT_MASKED,
            extra={"client_id": str(client_id)} if client_id else None, skip_if_empty=skip_if_empty,
        )

    async def list(self, q: str | None, active_only: bool) -> list[Any]:
        return await self.repo.list((q or "").strip() or None, active_only)

    async def _ensure_unique_name(self, name: str, exclude: UUID | None = None) -> None:
        """Nama yang sama (abaikan huruf besar/kecil dan spasi di ujung) = klien yang sama: pakai yang sudah ada."""
        existing = await self.repo.find_by_name(name, exclude)
        if existing is not None:
            raise AppError("CLIENT_EXISTS", f"Klien \"{existing.name}\" sudah ada. Pilih klien yang sudah ada.",
                           status=409, details={"client_id": str(existing.client_id), "name": existing.name})

    async def get(self, client_id: UUID) -> Any:
        row = await self.repo.get(client_id)
        if row is None:
            raise NotFoundError("Klien")
        return row

    async def create(self, data: ClientCreate, user: CurrentUser) -> Any:
        code = data.client_code.strip().upper()
        if await self.repo.code_taken(code):
            raise AppError("CLIENT_CODE_TAKEN", CODE_TAKEN, status=409)
        await self._ensure_unique_name(data.name)
        row = await self.repo.insert({**data.model_dump(), "client_code": code, "name": data.name.strip()})
        await self._audit(user, "CLIENT_CREATE", row.client_id, None, row)
        return row

    async def _check_manage(self, client_id: UUID, user: CurrentUser) -> None:
        """Klien yang sudah punya proyek hanya diubah/dihapus PM/OM divisi pemilik proyek (atau SUPER_ADMIN)."""
        row = await self.get(client_id)
        if is_admin(user) or not row.project_count:
            return
        if not await self.repo.manages_via_project(client_id, user.employee_id):
            raise ForbiddenError("Klien ini punya proyek di divisi lain; hanya PM/OM divisi itu yang mengubahnya.")

    async def update(self, client_id: UUID, data: ClientUpdate, user: CurrentUser) -> Any:
        await self._check_manage(client_id, user)
        before = await self.get(client_id)
        fields = data.model_dump(exclude_unset=True)
        if fields.get("client_code"):
            fields["client_code"] = fields["client_code"].strip().upper()
            if await self.repo.code_taken(fields["client_code"], exclude=client_id):
                raise AppError("CLIENT_CODE_TAKEN", CODE_TAKEN, status=409)
        if fields.get("name"):
            fields["name"] = fields["name"].strip()
            await self._ensure_unique_name(fields["name"], exclude=client_id)
        row = await self.repo.update(client_id, fields)
        await self._audit(user, "CLIENT_UPDATE", client_id, before, row, skip_if_empty=True)
        return row

    async def delete(self, client_id: UUID, user: CurrentUser) -> None:
        await self._check_manage(client_id, user)
        row = await self.get(client_id)
        if row.project_count:
            raise AppError("CLIENT_IN_USE", f"Klien masih punya {row.project_count} proyek. Nonaktifkan saja.",
                           status=409)
        await self.repo.archive(client_id)
        await self._audit(user, "CLIENT_DELETE", client_id, row, None)

    # ── Client Sites ────────────────────────────────────────────────────────
    async def list_sites(self, client_id: UUID) -> Sequence[Any]:
        await self.get(client_id)
        return await self.repo.list_sites(client_id)

    async def get_site(self, site_id: UUID) -> Any:
        site = await self.repo.get_site(site_id)
        if site is None:
            raise NotFoundError("Cabang / Lokasi Klien (Site)")
        return site

    async def create_site(self, client_id: UUID, data: ClientSiteCreate, user: CurrentUser) -> Any:
        await self._check_manage(client_id, user)
        row = await self.repo.create_site(client_id, data.model_dump())
        await self._audit(user, "CLIENT_SITE_CREATE", row.site_id, None, row, site=True, client_id=client_id)
        return row

    async def update_site(self, client_id: UUID, site_id: UUID, data: ClientSiteUpdate, user: CurrentUser) -> Any:
        await self._check_manage(client_id, user)
        before = await self.get_site(site_id)
        fields = data.model_dump(exclude_unset=True)
        row = await self.repo.update_site(site_id, fields)
        await self._audit(user, "CLIENT_SITE_UPDATE", site_id, before, row, site=True, client_id=client_id,
                          skip_if_empty=True)
        return row

    async def delete_site(self, client_id: UUID, site_id: UUID, user: CurrentUser) -> None:
        await self._check_manage(client_id, user)
        before = await self.get_site(site_id)
        await self.repo.delete_site(site_id)
        await self._audit(user, "CLIENT_SITE_DELETE", site_id, before, None, site=True, client_id=client_id)

    async def get_with_sites(self, client_id: UUID) -> dict[str, Any]:
        client = await self.get(client_id)
        sites = await self.repo.list_sites(client_id)
        return {**dict(client._mapping), "sites": [dict(s._mapping) for s in sites]}

