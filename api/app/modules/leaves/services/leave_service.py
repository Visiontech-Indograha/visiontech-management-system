"""
app/modules/leaves/services/leave_service.py

Service logika bisnis cuti, izin, dan sakit.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.hard_delete import write_delete_audit
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.core.time import jakarta_now
from app.modules.leaves.repositories.leave_repository import LeaveRepository
from app.modules.leaves.schemas.leave_schema import LeaveCancel, LeaveCreate, LeaveReview
from app.modules.notifications.services.notification_service import NotificationService
from app.shared.access.office_scope import ensure_employee_in_scope, office_restriction, offices_param

# Batas mundur tanggal mulai cuti (hari, zona Jakarta) untuk pemohon biasa. Web dan mobile harus memakai angka sama.
LEAVE_MAX_BACKDATE_DAYS = 3


def _today() -> date:
    return jakarta_now().date()


LEAVE_TYPES = (
    ("ANNUAL", "Cuti tahunan", True),
    ("SICK", "Sakit", False),
    ("MATERNITY", "Cuti melahirkan", False),
    ("UNPAID", "Cuti tanpa gaji", False),
    ("OTHER", "Izin lainnya", False),
)
CANCELLABLE_STATUSES = ("PENDING", "APPROVED_BY_PM", "APPROVED_BY_HR")
# Status yang sudah memotong kuota cuti tahunan (dikembalikan saat dibatalkan)
QUOTA_HELD_STATUSES = ("APPROVED_BY_PM", "APPROVED_BY_HR")
ALLOWED_REVIEW_ROLES = ("PROJECT_MANAGER", "ADMIN_HR_GA", "OPERATIONAL_MANAGER", "SUPER_ADMIN")
ORG_WIDE_ROLES = ("ADMIN_HR_GA", "OPERATIONAL_MANAGER", "SUPER_ADMIN")
CANCEL_ROLES = ("ADMIN_HR_GA", "OPERATIONAL_MANAGER")


def _conflict_dict(row: Any) -> dict[str, Any]:
    """Konflik jadwal dalam bentuk JSON-aman (dipakai respons dan detail galat 409)."""
    return {
        "plan_id": str(row.plan_id),
        "work_date": row.work_date.isoformat(),
        "team_name": row.team_name,
        "status": row.status,
    }


def _fmt_date(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


class LeaveService:
    """Logika alur persetujuan cuti dan pengurangan kuota."""

    def __init__(self, repo: LeaveRepository) -> None:
        self.repo = repo

    def _notify(self) -> NotificationService:
        return NotificationService(self.repo.db)

    async def _hr_offices(self, user: CurrentUser) -> list[str] | None:
        """None = semua kantor. Akses cuti lewat peran HR (bukan SA/OM) dibatasi ke kantor jangkauannya bila
        ROLE_ASSIGNMENT_ENABLED (ADR 0002); cuti sendiri dan jalur PM tidak terpengaruh."""
        restriction = await office_restriction(self.repo.db, user, Permission.MANAGE_USERS,
                                               ("SUPER_ADMIN", "OPERATIONAL_MANAGER"))
        return None if restriction is None else offices_param(restriction)

    async def _hr_scope_ok(self, user: CurrentUser, employee_id: UUID | str) -> bool:
        if await self._hr_offices(user) is None:
            return True
        try:
            await ensure_employee_in_scope(self.repo.db, user, Permission.MANAGE_USERS, employee_id)
        except NotFoundError:
            return False
        return True

    async def apply(self, user: CurrentUser, data: LeaveCreate) -> Any:
        # Karyawan biasa hanya boleh mengajukan cuti untuk dirinya sendiri
        emp_id: UUID | str | None
        if not user.has_role("ADMIN_HR_GA", "OPERATIONAL_MANAGER", "SUPER_ADMIN"):
            if data.employee_id and str(data.employee_id) != str(user.employee_id):
                raise ForbiddenError("Hanya HR atau Admin yang dapat mengajukan cuti atas nama karyawan lain.")
            emp_id = user.employee_id
        else:
            emp_id = data.employee_id or user.employee_id
            if (emp_id is not None and str(emp_id) != str(user.employee_id)
                    and not await self._hr_scope_ok(user, emp_id)):
                raise NotFoundError("Karyawan")

        if emp_id is None:
            raise ValidationError("Karyawan pemohon cuti wajib ditentukan.")

        if data.end_date < data.start_date:
            raise ValidationError("Tanggal akhir cuti tidak boleh sebelum tanggal mulai.")

        # Cuti mundur lebih dari batas hanya boleh dicatatkan HR/Admin
        if (not user.has_role("ADMIN_HR_GA", "OPERATIONAL_MANAGER", "SUPER_ADMIN")
                and data.start_date < _today() - timedelta(days=LEAVE_MAX_BACKDATE_DAYS)):
            raise ValidationError(
                f"Tanggal mulai cuti paling lambat {LEAVE_MAX_BACKDATE_DAYS} hari ke belakang. "
                "Hubungi HR untuk cuti yang lebih lama."
            )

        # Cegah permohonan dengan tanggal bertabrakan (overlapping) dengan cuti aktif/pending
        if await self.repo.has_overlapping_leave(emp_id, data.start_date, data.end_date):
            raise ValidationError("Anda sudah memiliki permohonan cuti aktif pada rentang tanggal tersebut.")

        # Hitung hari kerja efektif: kecualikan hari Minggu sebagai hari libur mingguan resmi
        total_days = sum(
            1 for i in range((data.end_date - data.start_date).days + 1)
            if (data.start_date + timedelta(days=i)).weekday() != 6
        )
        if total_days <= 0:
            raise ValidationError(
                "Permohonan cuti harus mencakup minimal 1 hari kerja efektif (bukan hari libur saja)."
            )

        year = data.start_date.year

        if data.leave_type == "ANNUAL":
            bal = await self.repo.get_or_create_balance(emp_id, year)
            if bal.remaining_quota < total_days:
                raise AppError(
                    "QUOTA_EXCEEDED",
                    f"Sisa kuota cuti tahunan ({bal.remaining_quota} hari) tidak mencukupi untuk "
                    f"pengajuan {total_days} hari.",
                    status=422,
                )

        leave_id = await self.repo.insert_leave(
            employee_id=emp_id,
            leave_type=data.leave_type,
            start_date=data.start_date,
            end_date=data.end_date,
            total_days=total_days,
            reason=data.reason.strip(),
            attachment_path=str(data.attachment_file_id) if data.attachment_file_id else None,
            status="PENDING",
        )
        notifier = self._notify()
        who = await notifier.employee_name(emp_id)
        span = f"{data.start_date:%d/%m/%Y} - {data.end_date:%d/%m/%Y}"
        await notifier.notify_division_managers(
            emp_id, "LEAVE_REQUESTED", f"{who} mengajukan cuti/izin", span, target="leave",
            roles=("PROJECT_MANAGER", "OPERATIONAL_MANAGER", "ADMIN_HR_GA"),
        )
        return await self.repo.get_leave(leave_id)

    async def review(self, user: CurrentUser, leave_id: UUID, data: LeaveReview) -> Any:
        if not user.has_role(*ALLOWED_REVIEW_ROLES):
            raise ForbiddenError("Hanya PM, HR, OM, atau Super Admin yang berwenang meninjau permohonan cuti.")

        if user.employee_id is None:
            raise ForbiddenError("Akun peninjau cuti wajib tertaut ke data karyawan.")

        # Dikunci agar dua peninjau bersamaan tidak sama-sama membaca PENDING lalu memotong kuota dua kali.
        leave = await self.repo.get_leave(leave_id, for_update=True)
        if leave is None:
            raise NotFoundError("Permohonan cuti")
        pm_path = user.has_role("PROJECT_MANAGER") and await self._pm_owns(user, leave.employee_id)
        if not pm_path and not await self._hr_scope_ok(user, leave.employee_id):
            raise NotFoundError("Permohonan cuti")

        if str(user.employee_id) == str(leave.employee_id):
            raise ForbiddenError("Pemohon cuti tidak dapat menyetujui atau menolak permohonannya sendiri.")

        if not pm_path and not user.has_role(*ORG_WIDE_ROLES):
            raise ForbiddenError("PM hanya dapat meninjau cuti karyawan di divisinya.")

        if leave.status in ("APPROVED_BY_HR", "REJECTED", "CANCELLED"):
            raise AppError("ALREADY_DECIDED", "Permohonan cuti ini sudah diputuskan.", status=409)

        # PM yang juga HR/OM/SA memutus sebagai peran lebarnya (satu langkah), bukan sebagai PM divisi.
        is_pm = pm_path and not user.has_role(*ORG_WIDE_ROLES)
        if is_pm and leave.status == "APPROVED_BY_PM":
            raise AppError(
                "ALREADY_APPROVED_BY_PM",
                "Permohonan cuti ini sudah disetujui PM dan menunggu persetujuan HR.",
                status=409,
            )

        new_status = "REJECTED" if data.decision == "REJECTED" else ("APPROVED_BY_PM" if is_pm else "APPROVED_BY_HR")

        # Cuti yang bertabrakan dengan jadwal tim berjalan hanya boleh disetujui bila peninjau mengonfirmasinya
        conflicts: list[dict[str, Any]] = []
        if data.decision == "APPROVED":
            conflicts = await self._conflicts_of(leave.employee_id, leave.start_date, leave.end_date)
            if conflicts and not data.acknowledge_conflicts:
                raise AppError(
                    "LEAVE_CONFLICT",
                    "Pemohon masih terjadwal di tim pada hari cuti. Konfirmasi konflik jadwal untuk tetap menyetujui.",
                    status=409,
                    details={"conflicts": conflicts},
                )

        if not await self.repo.update_review(
            leave_id=leave_id,
            status=new_status,
            reviewer_id=user.employee_id,
            is_pm=is_pm,
            note=data.note.strip() if data.note else None,
            expected=leave.status,
        ):
            raise AppError("INVALID_STATE", "Status cuti sudah berubah; muat ulang lalu coba lagi.", status=409)

        # Potong kuota cuti tahunan hanya saat disetujui pertama kali (mencegah double deduction)
        # Serta kembalikan saldo (refund) jika persetujuan awal PM kemudian ditolak oleh HR
        if leave.leave_type == "ANNUAL":
            if data.decision == "APPROVED" and leave.status == "PENDING":
                # Pemotongan pertama kali (baik oleh PM maupun langsung oleh HR)
                if not await self.repo.deduct_balance(leave.employee_id, leave.start_date.year, leave.total_days):
                    raise AppError(
                        "QUOTA_EXCEEDED",
                        "Sisa kuota cuti tahunan karyawan tidak mencukupi untuk menyetujui pengajuan ini.",
                        status=422,
                    )
            elif data.decision == "REJECTED" and leave.status == "APPROVED_BY_PM":
                # Pengembalian kuota karena sebelumnya sudah dipotong saat disetujui PM
                await self.repo.deduct_balance(leave.employee_id, leave.start_date.year, -leave.total_days)

        notifier = self._notify()
        verdict = {
            "REJECTED": "ditolak",
            "APPROVED_BY_PM": "disetujui PM (menunggu HR)",
            "APPROVED_BY_HR": "disetujui",
        }[new_status]
        await notifier.notify_employees(
            [leave.employee_id], "LEAVE_DECIDED", f"Cuti/izin Anda {verdict}",
            data.note.strip() if data.note else "", target="leave",
        )
        if new_status == "APPROVED_BY_PM":
            await notifier.notify_roles(
                ["ADMIN_HR_GA"], "LEAVE_REQUESTED",
                f"Cuti {await notifier.employee_name(leave.employee_id)} menunggu persetujuan HR", "", target="leave",
            )
        if conflicts:
            who = await notifier.employee_name(leave.employee_id)
            detail = "; ".join(
                f"{c['team_name']} {_fmt_date(c['work_date'])}" for c in conflicts
            )
            await notifier.notify_division_managers(
                leave.employee_id, "LEAVE_CONFLICT", f"{who} cuti pada jadwal tim", detail, target="leave",
                roles=("PROJECT_MANAGER",),
            )
        return await self.repo.get_leave(leave_id)

    async def cancel(self, user: CurrentUser, leave_id: UUID, data: LeaveCancel | None = None) -> Any:
        # Dikunci agar pembatalan tidak berbarengan dengan persetujuan (pengembalian kuota ganda)
        leave = await self.repo.get_leave(leave_id, for_update=True)
        if leave is None:
            raise NotFoundError("Permohonan cuti")
        is_owner = user.employee_id is not None and str(user.employee_id) == str(leave.employee_id)
        if not is_owner and not user.has_role(*CANCEL_ROLES):
            raise ForbiddenError("Hanya pemohon, HR, atau OM yang dapat membatalkan permohonan cuti ini.")
        if leave.status not in CANCELLABLE_STATUSES:
            raise AppError("NOT_CANCELLABLE", "Permohonan cuti ini sudah tidak dapat dibatalkan.", status=409)
        if leave.end_date < jakarta_now().date():
            raise AppError(
                "NOT_CANCELLABLE", "Cuti yang hari terakhirnya sudah lewat tidak dapat dibatalkan.", status=409,
            )

        reason = ((data.reason or "").strip() if data else "") or None
        if not await self.repo.cancel_leave(leave_id, reason, leave.status):
            raise AppError("NOT_CANCELLABLE", "Status cuti sudah berubah; muat ulang lalu coba lagi.", status=409)
        # Kuota tahunan sudah dipotong saat persetujuan pertama; kembalikan sesuai status sebelum dibatalkan
        if leave.leave_type == "ANNUAL" and leave.status in QUOTA_HELD_STATUSES:
            await self.repo.deduct_balance(leave.employee_id, leave.start_date.year, -leave.total_days)
        await write_delete_audit(
            self.repo.db, actor_user_id=user.user_id, actor_role=user.role, actor_email=user.email,
            entity_type="leave_request", entity_id=leave_id, action="LEAVE_CANCEL",
            detail={
                "before": leave.status, "after": "CANCELLED", "by_owner": is_owner,
                "quota_refunded": leave.leave_type == "ANNUAL" and leave.status in QUOTA_HELD_STATUSES,
            },
        )

        notifier = self._notify()
        who = await notifier.employee_name(leave.employee_id)
        await notifier.notify_division_managers(
            leave.employee_id, "LEAVE_CANCELLED",
            f"{who} membatalkan pengajuan cuti/izin" if is_owner else f"Cuti {who} dibatalkan",
            reason or "", target="leave",
        )
        if not is_owner:
            await notifier.notify_employees(
                [leave.employee_id], "LEAVE_CANCELLED", "Cuti/izin Anda dibatalkan", reason or "", target="leave",
            )
        return await self.repo.get_leave(leave_id)

    async def _conflicts_of(self, employee_id: UUID | str, start: date, end: date) -> list[dict[str, Any]]:
        rows = await self.repo.schedule_conflicts([str(employee_id)], start, end)
        return [_conflict_dict(r) for r in rows]

    async def conflicts_for(self, rows: Iterable[Any]) -> dict[str, list[dict[str, Any]]]:
        """Konflik jadwal tim per cuti (kunci: leave_id). Satu kueri untuk seluruh daftar."""
        rows = list(rows)
        if not rows:
            return {}
        found = await self.repo.schedule_conflicts(
            sorted({str(r.employee_id) for r in rows}),
            min(r.start_date for r in rows),
            max(r.end_date for r in rows),
        )
        by_emp: dict[str, list[Any]] = defaultdict(list)
        for c in found:
            by_emp[str(c.employee_id)].append(c)
        return {
            str(r.leave_id): [
                _conflict_dict(c)
                for c in by_emp.get(str(r.employee_id), [])
                if r.start_date <= c.work_date <= r.end_date
            ]
            for r in rows
        }

    async def _pm_owns(self, user: CurrentUser, employee_id: UUID | str) -> bool:
        pm_id = await self.repo.division_pm_of(employee_id)
        return pm_id is not None and str(pm_id) == str(user.employee_id)

    async def _ensure_can_view(self, user: CurrentUser, employee_id: UUID | str) -> None:
        if str(employee_id) == str(user.employee_id):
            return
        if user.has_role(*ORG_WIDE_ROLES) and await self._hr_scope_ok(user, employee_id):
            return
        if user.has_role("PROJECT_MANAGER") and await self._pm_owns(user, employee_id):
            return
        raise ForbiddenError("Anda tidak berhak melihat data cuti karyawan ini.")

    async def get(self, user: CurrentUser, leave_id: UUID) -> Any:
        leave = await self.repo.get_leave(leave_id)
        if leave is None:
            raise NotFoundError("Permohonan cuti")
        await self._ensure_can_view(user, leave.employee_id)
        return leave

    async def list(
        self,
        user: CurrentUser,
        *,
        employee_id: UUID | None = None,
        status: str | None = None,
        year: int | None = None,
    ) -> list[Any]:
        pm_id = None
        if user.has_role("PROJECT_MANAGER") and not user.has_role(*ORG_WIDE_ROLES):
            pm_id = user.employee_id
        elif not user.has_role(*ORG_WIDE_ROLES):
            if user.employee_id is None:
                return []
            employee_id = UUID(str(user.employee_id))
        offices = await self._hr_offices(user) if pm_id is None and user.has_role(*ORG_WIDE_ROLES) else None
        return list(
            await self.repo.list_leaves(employee_id=employee_id, status=status, year=year, pm_id=pm_id,
                                        offices=offices)
        )

    async def balance(self, user: CurrentUser, employee_id: UUID, year: int) -> Any:
        await self._ensure_can_view(user, employee_id)
        bal = await self.repo.get_or_create_balance(employee_id, year)
        return bal
