"""Aturan penugasan peran tambahan (ADR 0002 bagian 8 dan 12). Hanya SUPER_ADMIN (izin di route)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.hard_delete import write_delete_audit
from app.core.security import CurrentUser
from app.modules.role_assignments.repositories.role_assignment_repository import RoleAssignmentRepository

HR, FINANCE, OM, SA = "ADMIN_HR_GA", "FINANCE", "OPERATIONAL_MANAGER", "SUPER_ADMIN"
PHASE1_ROLES = {HR, FINANCE, OM}
MAX_EXTRA_ROLES = 2


class RoleAssignmentService:
    def __init__(self, repo: RoleAssignmentRepository) -> None:
        self.repo = repo

    async def _audit(self, actor: CurrentUser, target: UUID, action: str, detail: dict[str, Any]) -> None:
        await write_delete_audit(
            self.repo.db, actor_user_id=actor.user_id, actor_role=actor.role, actor_email=actor.email,
            entity_type="users", entity_id=target, action=action, detail=detail,
        )

    @staticmethod
    def _not_self(actor: CurrentUser, user_id: UUID) -> None:
        if str(user_id) == str(actor.user_id):
            raise ValidationError("Anda tidak bisa mengubah penugasan peran akun Anda sendiri.")

    async def list_for_user(self, user_id: UUID) -> list[Any]:
        if not await self.repo.user_exists(user_id):
            raise NotFoundError("Pengguna")
        return await self.repo.list_active(user_id)

    async def add(self, actor: CurrentUser, user_id: UUID, role: str, office_id: UUID | None) -> Any:
        self._not_self(actor, user_id)
        target = await self.repo.lock_user(user_id)  # kunci: cek batas/larangan lalu tulis tidak boleh balapan
        if target is None:
            raise NotFoundError("Pengguna")
        if role not in PHASE1_ROLES:
            raise ValidationError("Peran ini belum bisa ditambahkan. Pilih HR/GA, Finance, atau Operational Manager.")
        primary = target.system_role
        if primary == SA:
            raise ValidationError("Super Admin tidak bisa digabung dengan peran lain.")
        if role == OM:
            if office_id is not None:
                raise ValidationError("Operational Manager berlaku untuk semua kantor. Kosongkan pilihan kantor.")
            if primary == OM:
                raise ValidationError("Akun ini sudah menjadi Operational Manager.")
        elif office_id is None:
            raise ValidationError("Pilih kantor untuk peran ini.")
        elif not await self.repo.office_active(office_id):
            raise ValidationError("Kantor tidak ditemukan atau sudah tidak aktif.")

        current = await self.repo.list_active(user_id)
        roles = {primary} | {r.role for r in current}
        if any(r.role == role and r.office_id == office_id for r in current):
            raise ValidationError("Penugasan ini sudah ada.")
        if {HR, FINANCE} <= (roles | {role}):
            raise ValidationError("Peran HR/GA dan Finance tidak boleh dipegang orang yang sama.")
        if len((roles | {role}) - {primary}) > MAX_EXTRA_ROLES:
            raise ValidationError(f"Satu akun hanya boleh punya {MAX_EXTRA_ROLES} peran tambahan.")

        row = await self.repo.insert(user_id, role, office_id, actor.user_id)
        await self._audit(actor, user_id, "ROLE_ASSIGNMENT_ADD", {
            "assignment_id": str(row.assignment_id), "role": role,
            "office_id": str(office_id) if office_id else None,
            "before": sorted(roles), "after": sorted(roles | {role}),
        })
        created = await self.repo.get_active(user_id, row.assignment_id)
        if created is None:  # tidak mungkin: baru ditulis di transaksi yang sama
            raise AppError("INTERNAL", "Penugasan gagal disimpan.", status=500)
        return created

    async def revoke(self, actor: CurrentUser, user_id: UUID, assignment_id: UUID) -> None:
        self._not_self(actor, user_id)
        if await self.repo.lock_user(user_id) is None:
            raise NotFoundError("Pengguna")
        row = await self.repo.get_active(user_id, assignment_id)
        if row is None:
            raise NotFoundError("Penugasan")
        if row.source == "PRIMARY":
            raise ValidationError("Peran utama tidak bisa dicabut di sini.")
        if await self.repo.revoke(assignment_id, actor.user_id) != 1:
            raise NotFoundError("Penugasan")
        await self.repo.revoke_device_credentials(user_id)
        await self._audit(actor, user_id, "ROLE_ASSIGNMENT_REVOKE", {
            "assignment_id": str(assignment_id), "role": row.role,
            "office_id": str(row.office_id) if row.office_id else None,
        })
