"""
app/shared/attachments/service.py
Lampiran pengajuan lembur dan mess (bukti kerja, surat tugas, identitas): maksimal 5 berkas per pengajuan.

Aturan:
- Berkas diunggah dulu lewat POST /files/upload (MIME, magic bytes, ukuran dicek di sana), lalu ditautkan di sini.
  Hanya berkas unggahan sendiri, dari kantor yang sama.
- Pemohon dan peninjau boleh melihat/menambah. Orang lain di kantor yang sama 403; kantor lain atau pengajuan
  tidak ada 404.
- Terkunci setelah pengajuan diputuskan/dibatalkan (status bukan "menunggu"): tidak bisa tambah/hapus (409).
  Baris induk dikunci FOR UPDATE, jadi keputusan yang bersamaan tidak menyisakan lampiran baru.
- Menghapus lampiran melepas berkas bila tak dirujuk data lain; objeknya dihapus setelah commit (file_cleanup).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import file_cleanup
from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.shared.access.access_service import DailyNeed, check_daily_access, is_admin
from app.shared.access.office_scope import ensure_employee_in_scope, office_restriction
from app.shared.attachments.repository import (
    MAX_ATTACHMENTS,
    MESS,
    OVERTIME,
    AttachmentKind,
    AttachmentRepository,
)

_ORG_WIDE_MESS = ("ADMIN_HR_GA", "OPERATIONAL_MANAGER", "SUPER_ADMIN")

__all__ = ["MESS", "OVERTIME", "AttachmentService", "can_view_attachment"]


async def _in_scope(db: AsyncSession, user: CurrentUser, perm: Permission, employee_id: str) -> bool:
    if await office_restriction(db, user, perm) is None:
        return True
    try:
        await ensure_employee_in_scope(db, user, perm, employee_id)
    except NotFoundError:
        return False
    return True


async def role_on(db: AsyncSession, repo: AttachmentRepository, kind: AttachmentKind, user: CurrentUser,
                  parent: Any) -> str | None:
    """'owner' | 'reviewer' | None. Peninjau mengikuti aturan keputusan modul asalnya."""
    if user.employee_id and str(user.employee_id) == parent.employee_id:
        return "owner"
    if is_admin(user):
        return "reviewer"
    perms = set(user.permissions)
    if kind is OVERTIME:
        if Permission.REVIEW_OVERTIME.value in perms and await _in_scope(
                db, user, Permission.REVIEW_OVERTIME, parent.employee_id):
            return "reviewer"
        if parent.daily_plan_id is not None:
            try:
                await check_daily_access(db, parent.daily_plan_id, user, DailyNeed.MANAGE)
                return "reviewer"
            except (NotFoundError, ForbiddenError):
                return None
        return None
    for perm in (Permission.REVIEW_MESS, Permission.MANAGE_MESS):
        if perm.value not in perms or not await _in_scope(db, user, perm, parent.employee_id):
            continue
        if user.has_role(*_ORG_WIDE_MESS):
            return "reviewer"
        if (user.has_role("PROJECT_MANAGER") and user.employee_id
                and await repo.division_pm_of(parent.employee_id) == str(user.employee_id)):
            return "reviewer"
    return None


def _locked() -> AppError:
    return AppError("LAMPIRAN_TERKUNCI",
                    "Pengajuan ini sudah diputuskan atau dibatalkan, jadi lampirannya tidak bisa diubah lagi.",
                    status=409)


class AttachmentService:
    def __init__(self, db: AsyncSession, kind: AttachmentKind) -> None:
        self.db = db
        self.kind = kind
        self.repo = AttachmentRepository(db)

    async def _authorize(self, user: CurrentUser, parent_id: UUID, *, lock: bool) -> tuple[Any, str]:
        parent = await self.repo.parent(self.kind, parent_id, lock=lock)
        if parent is None:
            raise NotFoundError(self.kind.label)
        role = await role_on(self.db, self.repo, self.kind, user, parent)
        if role is None:
            if parent.office_id != user.organization_id:
                raise NotFoundError(self.kind.label)  # kantor lain: keberadaan tidak dibocorkan
            raise ForbiddenError("Anda tidak berwenang melihat atau mengubah lampiran pengajuan ini.")
        return parent, role

    async def items(self, user: CurrentUser, parent_id: UUID) -> list[dict[str, Any]]:
        await self._authorize(user, parent_id, lock=False)
        return await self._rows(user, parent_id)

    async def _rows(self, user: CurrentUser, parent_id: UUID) -> list[dict[str, Any]]:
        return [{**r._mapping, "mine": r.added_by == user.user_id} for r in await self.repo.items(self.kind, parent_id)]

    async def add(self, user: CurrentUser, parent_id: UUID, file_id: UUID) -> list[dict[str, Any]]:
        parent, _ = await self._authorize(user, parent_id, lock=True)
        if parent.status != self.kind.pending_status:
            raise _locked()
        f = await self.repo.file(file_id)
        # Berkas orang lain / kantor lain tidak boleh dilampirkan: dijawab seolah tidak ada.
        if f is None or f.office_id != user.organization_id or f.uploaded_by != user.user_id:
            raise NotFoundError("Berkas")
        if await self.repo.get_link(self.kind, parent_id, file_id) is None:
            if await self.repo.count(self.kind, parent_id) >= MAX_ATTACHMENTS:
                raise AppError("LAMPIRAN_PENUH",
                               f"Lampiran sudah {MAX_ATTACHMENTS} berkas (batas). Hapus satu dulu bila ingin menambah.",
                               status=409)
            await self.repo.insert(self.kind, parent_id, file_id, parent.office_id, user.user_id)
        return await self._rows(user, parent_id)

    async def remove(self, user: CurrentUser, parent_id: UUID, file_id: UUID) -> list[dict[str, Any]]:
        parent, role = await self._authorize(user, parent_id, lock=True)
        if parent.status != self.kind.pending_status:
            raise _locked()
        link = await self.repo.get_link(self.kind, parent_id, file_id)
        if link is None:
            raise NotFoundError("Lampiran")
        if role != "owner" and not is_admin(user) and link.added_by != user.user_id:
            raise ForbiddenError("Peninjau hanya dapat menghapus lampiran yang diunggahnya sendiri.")
        key = await self.repo.storage_key(file_id)
        await self.repo.delete(self.kind, parent_id, file_id)
        if key:
            await file_cleanup.release_keys(self.db, [key])
        return await self._rows(user, parent_id)


async def can_view_attachment(db: AsyncSession, user: CurrentUser, kind: AttachmentKind, parent_id: str) -> bool:
    """Dipakai `check_file_access`: boleh membuka berkas yang terlampir pada pengajuan ini (pemohon/peninjau)."""
    repo = AttachmentRepository(db)
    parent = await repo.parent(kind, parent_id)
    return parent is not None and await role_on(db, repo, kind, user, parent) is not None
