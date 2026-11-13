"""Arsip & Pulihkan (BACKLOG B-29): daftar item yang sudah dihapus (soft delete) dan pemulihannya.

Hanya SUPER_ADMIN, OM, dan HR. Izin modul asal tetap berlaku (dipasang di rute). Peralatan/kendaraan mengikuti
cakupan kantor pengelola aset; item di luar kantor = 404. Pulihkan = `delete_at` dikosongkan lewat UPDATE bersyarat
(idempoten; konflik kode/nama dengan item aktif atau induk yang masih diarsipkan = 409). Data pribadi karyawan
(karyawan, dokumen karyawan) sengaja tidak dicakup: berkas dimusnahkan 30 hari setelah keluar (`core/retention`).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.exc import IntegrityError

from app.core import system_settings
from app.core.audit_log import record_audit
from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.archive.repositories.archive_repository import ArchiveRepository
from app.modules.archive.schemas.archive_modules import ARCHIVE_MODULES, ArchiveModule
from app.shared.access.office_scope import office_restriction, offices_param

ALLOWED_ROLES = ("SUPER_ADMIN", "OPERATIONAL_MANAGER", "ADMIN_HR_GA")
_CONFLICT = "RESTORE_CONFLICT"


def _module(key: str) -> ArchiveModule:
    mod = ARCHIVE_MODULES.get(key)
    if mod is None:
        raise NotFoundError("Arsip")
    return mod


class ArchiveService:
    def __init__(self, repo: ArchiveRepository) -> None:
        self.repo = repo

    @staticmethod
    def _check_role(user: CurrentUser) -> None:
        if not user.has_role(*ALLOWED_ROLES):
            raise ForbiddenError("Arsip hanya untuk Super Admin, Operational Manager, dan HR.")

    async def _offices(self, mod: ArchiveModule, user: CurrentUser) -> list[str] | None:
        """None = semua kantor. Hanya modul beraset (punya kantor) dan HR yang dibatasi kantor tugasnya."""
        if mod.office_col is None or not system_settings.role_assignment_enabled():
            return None
        restriction = await office_restriction(self.repo.db, user, Permission.MANAGE_ASSETS, ("SUPER_ADMIN",))
        return None if restriction is None else offices_param(restriction)

    async def list_deleted(self, key: str, user: CurrentUser) -> list[dict[str, Any]]:
        mod = _module(key)
        self._check_role(user)
        offices = await self._offices(mod, user)
        if offices is not None and not offices:
            return []
        rows = await self.repo.list_deleted(mod, offices)
        return [{"id": r.id, "module": mod.key, "name": r.name, "code": r.code, "deleted_at": r.delete_at}
                for r in rows]

    async def restore(self, key: str, item_id: str, user: CurrentUser) -> dict[str, Any]:
        mod = _module(key)
        self._check_role(user)
        row = await self.repo.get_any(mod, item_id)
        offices = await self._offices(mod, user)
        if row is None or (offices is not None and (row.office_id is None or row.office_id not in offices)):
            raise NotFoundError(mod.label)
        out = {"id": row.id, "module": mod.key, "name": row.name, "code": row.code, "deleted_at": None}
        if row.delete_at is None:
            return out  # idempoten: sudah aktif
        missing = await self.repo.missing_parent(mod, item_id)
        if missing:
            raise AppError(_CONFLICT, f"Data induk ({missing}) masih diarsipkan. Pulihkan atau ganti dulu.",
                           status=409)
        if await self.repo.unique_conflict(mod, item_id):
            raise AppError(_CONFLICT, mod.conflict_message, status=409)
        try:
            async with self.repo.db.begin_nested():
                done = await self.repo.restore(mod, item_id)
        except IntegrityError as exc:
            raise AppError(_CONFLICT, mod.conflict_message, status=409) from exc
        if not done:
            return out  # dipulihkan permintaan lain lebih dulu
        await record_audit(self.repo.db, user, action=f"{mod.table.upper()}_RESTORE", entity_type=mod.table,
                           entity_id=item_id, before={"delete_at": row.delete_at}, after={"delete_at": None},
                           fields=("delete_at",))
        return out
