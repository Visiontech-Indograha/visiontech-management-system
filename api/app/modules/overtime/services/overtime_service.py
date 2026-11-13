"""
app/modules/overtime/services/overtime_service.py
Lembur daily-first: ketua/anggota tim mengajukan lembur atas jadwal harian yang sedang berjalan (ONGOING);
PM/OM divisi jadwal itu memutuskan (bukan pengajunya sendiri). Rekap: pemegang review:overtime seluruhnya,
PM hanya divisinya.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.file_cleanup import release_keys
from app.core.hard_delete import purge_row, write_delete_audit
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.notifications.services.notification_service import NotificationService
from app.modules.overtime.repositories.overtime_repository import OvertimeRepository
from app.shared.access.access_service import DailyNeed, check_daily_access, is_admin, require_daily_status
from app.shared.access.office_scope import ensure_employee_in_scope, office_restriction, offices_param


def _state(msg: str) -> AppError:
    return AppError("INVALID_STATE", msg, status=409)


class OvertimeService:
    """Pengajuan & persetujuan lembur."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = OvertimeRepository(db)

    async def delete(self, overtime_id: UUID, actor: CurrentUser) -> None:
        """Hapus permanen pengajuan lembur (SUPER_ADMIN) + audit."""
        exists = await self.repo.fetchone("SELECT 1 FROM overtime WHERE overtime_id = CAST(:id AS uuid) FOR UPDATE",
                                          {"id": str(overtime_id)})
        if exists is None:
            raise NotFoundError("Lembur")
        keys = [str(r[0]) for r in (await self.repo.fetchall(
            "SELECT f.storage_key FROM overtime_attachment a JOIN file_object f ON f.id = a.file_object_id "
            "WHERE a.overtime_id = CAST(:id AS uuid)", {"id": str(overtime_id)}))]
        await purge_row(self.db, "overtime", "overtime_id", overtime_id)
        await release_keys(self.db, keys)  # lampirannya ikut terhapus (objek dibuang setelah commit)
        await write_delete_audit(
            self.db, actor_user_id=actor.user_id,
            actor_role=actor.role,
            actor_email=actor.email, entity_type="overtime", entity_id=overtime_id,
        )

    async def report(self, user: CurrentUser, daily_plan_id: UUID, hours: float, reason: str) -> Any:
        access = await check_daily_access(self.db, daily_plan_id, user, DailyNeed.TEAM)
        require_daily_status(access, "ONGOING")
        if not 0 < hours <= 12:
            raise ValidationError("Jam lembur harus lebih dari 0 dan paling banyak 12 jam.")
        reason = reason.strip()
        if not reason:
            raise ValidationError("Alasan lembur wajib diisi.")
        employee_id = user.employee_id or ""
        if await self.repo.duplicate(daily_plan_id, employee_id):
            raise _state("Pengajuan lembur Anda untuk jadwal ini sudah ada dan sedang diproses.")
        overtime_id = await self.repo.insert(daily_plan_id, employee_id, access.plan.work_date, hours, reason)
        notifier = NotificationService(self.db)
        if employee_id:
            await notifier.notify_division_managers(
                employee_id, "OVERTIME_REQUESTED",
                f"{await notifier.employee_name(employee_id)} mengajukan lembur {hours:g} jam",
                reason,
                target="overtime",
            )
        return await self.repo.get(overtime_id)

    async def review(self, user: CurrentUser, overtime_id: UUID, decision: str, note: str | None) -> Any:
        ot = await self.repo.get(overtime_id)
        if ot is None:
            raise NotFoundError("Lembur")
        if await self._offices(user) is not None:
            await ensure_employee_in_scope(self.db, user, Permission.REVIEW_OVERTIME, ot.employee_id, "Lembur")
        if ot.status != "PENDING_PM":
            raise _state("Pengajuan lembur ini sudah diperiksa.")
        if ot.daily_plan_id is None:
            if not is_admin(user):
                raise ForbiddenError("Lembur tanpa jadwal hanya dapat diperiksa admin.")
        else:
            await check_daily_access(self.db, ot.daily_plan_id, user, DailyNeed.MANAGE)
        if user.employee_id is None or user.employee_id == str(ot.employee_id):
            raise ForbiddenError("Pengaju lembur tidak dapat memutuskan pengajuannya sendiri.")
        if decision not in ("APPROVED", "REJECTED"):
            raise ValidationError("Keputusan harus disetujui atau ditolak.")
        if not await self.repo.review(overtime_id, user.employee_id, decision, (note or "").strip() or None):
            raise _state("Pengajuan lembur ini sudah diperiksa.")
        verdict = "disetujui" if decision == "APPROVED" else "ditolak"
        await NotificationService(self.db).notify_employees(
            [ot.employee_id], "OVERTIME_DECIDED", f"Lembur Anda {verdict}", (note or "").strip(), target="overtime",
        )
        return await self.repo.get(overtime_id)

    async def _offices(self, user: CurrentUser) -> list[str] | None:
        """None = semua kantor. Finance (bukan SA/OM) dibatasi ke kantor jangkauannya bila ROLE_ASSIGNMENT_ENABLED
        (ADR 0002)."""
        restriction = await office_restriction(self.db, user, Permission.REVIEW_OVERTIME,
                                               ("SUPER_ADMIN", "OPERATIONAL_MANAGER"))
        return None if restriction is None else offices_param(restriction)

    async def list_overtimes(
        self,
        user: CurrentUser,
        daily_plan_id: UUID | None = None,
        *,
        after: tuple[Any, ...] | None = None,
        limit: int | None = None,
        status: str | None = None,
        q: str | None = None,
        mine: bool = False,
    ) -> Sequence[Any]:
        """Cakupan akses sama untuk kedua mode; `after` != None = keyset (limit baris, filter di SQL)."""
        own = str(user.employee_id) if mine and user.employee_id else None
        if mine and own is None:
            return []  # mine hanya mempersempit; tanpa employee tidak ada lembur milik sendiri
        if daily_plan_id:
            await check_daily_access(self.db, daily_plan_id, user, DailyNeed.LOGISTICS)
            return await self.repo.list_by_plan(daily_plan_id, after, limit, status, q, mine=own)
        if is_admin(user) or Permission.REVIEW_OVERTIME.value in user.permissions:
            return await self.repo.list_all_active(None, after, limit, status, q, await self._offices(user), mine=own)
        if user.has_role("PROJECT_MANAGER") and user.employee_id:
            return await self.repo.list_all_active(user.employee_id, after, limit, status, q, mine=own)
        if user.employee_id:
            return await self.repo.list_by_employee(user.employee_id, after, limit, status, q)
        return []

    async def with_review_flags(self, user: CurrentUser, rows: Sequence[Any]) -> list[dict[str, Any]]:
        """Baris lembur + `can_review`, dengan aturan yang sama seperti review(): pending, bukan pengaju sendiri,
        dan PM/OM divisi jadwal (atau admin). Kueri tambahan hanya bila ada baris pending non-admin."""
        pending = [r._mapping for r in rows if r._mapping["status"] == "PENDING_PM"]
        managed: set[str] = set()
        if user.employee_id and not is_admin(user) and pending:
            managed = await self.repo.managed_pending_plan_ids(user.employee_id)
        out: list[dict[str, Any]] = []
        for r in rows:
            m = dict(r._mapping)
            plan = str(m["daily_plan_id"]) if m["daily_plan_id"] is not None else None
            m["can_review"] = bool(
                user.employee_id
                and m["status"] == "PENDING_PM"
                and str(m["employee_id"]) != user.employee_id
                and (is_admin(user) or (plan is not None and plan in managed))
            )
            out.append(m)
        return out

    async def list_by_plan(self, user: CurrentUser, daily_plan_id: UUID) -> Sequence[Any]:
        await check_daily_access(self.db, daily_plan_id, user, DailyNeed.LOGISTICS)
        return await self.repo.list_by_plan(daily_plan_id)

    async def recap(self, user: CurrentUser, month: date | None) -> Sequence[Any]:
        if is_admin(user) or Permission.REVIEW_OVERTIME.value in user.permissions:
            return await self.repo.recap(month, None, await self._offices(user))
        if user.has_role("PROJECT_MANAGER") and user.employee_id:
            return await self.repo.recap(month, user.employee_id)
        raise ForbiddenError("Rekap lembur hanya untuk OM, PM divisi, atau admin.")
