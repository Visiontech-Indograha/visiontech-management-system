"""
app/modules/leaves/services/leave_service.py

Service logika bisnis cuti, izin, dan sakit.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.security import CurrentUser
from app.modules.leaves.repositories.leave_repository import LeaveRepository
from app.modules.leaves.schemas.leave_schema import LeaveCreate, LeaveReview
from app.modules.notifications.services.notification_service import NotificationService

LEAVE_TYPES = (
    ("ANNUAL", "Cuti tahunan", True),
    ("SICK", "Sakit", False),
    ("MATERNITY", "Cuti melahirkan", False),
    ("UNPAID", "Cuti tanpa gaji", False),
    ("OTHER", "Izin lainnya", False),
)
CANCELLABLE_STATUSES = ("PENDING", "APPROVED_BY_PM")
ALLOWED_REVIEW_ROLES = ("PROJECT_MANAGER", "ADMIN_HR_GA", "OPERATIONAL_MANAGER", "SUPER_ADMIN")
ORG_WIDE_ROLES = ("ADMIN_HR_GA", "OPERATIONAL_MANAGER", "SUPER_ADMIN")


class LeaveService:
    """Logika alur persetujuan cuti dan pengurangan kuota."""

    def __init__(self, repo: LeaveRepository) -> None:
        self.repo = repo

    def _notify(self) -> NotificationService:
        return NotificationService(self.repo.db)

    async def apply(self, user: CurrentUser, data: LeaveCreate) -> Any:
        # Karyawan biasa hanya boleh mengajukan cuti untuk dirinya sendiri
        emp_id: UUID | str | None
        if user.role not in ("ADMIN_HR_GA", "OPERATIONAL_MANAGER", "SUPER_ADMIN"):
            if data.employee_id and str(data.employee_id) != str(user.employee_id):
                raise ForbiddenError("Hanya HR atau Admin yang dapat mengajukan cuti atas nama karyawan lain.")
            emp_id = user.employee_id
        else:
            emp_id = data.employee_id or user.employee_id

        if emp_id is None:
            raise ValidationError("Karyawan pemohon cuti wajib ditentukan.")

        if data.end_date < data.start_date:
            raise ValidationError("Tanggal akhir cuti tidak boleh sebelum tanggal mulai.")

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
        if user.role not in ALLOWED_REVIEW_ROLES:
            raise ForbiddenError("Hanya PM, HR, OM, atau Super Admin yang berwenang meninjau permohonan cuti.")

        if user.employee_id is None:
            raise ForbiddenError("Akun peninjau cuti wajib tertaut ke data karyawan.")

        leave = await self.repo.get_leave(leave_id)
        if leave is None:
            raise NotFoundError("Permohonan cuti")

        if str(user.employee_id) == str(leave.employee_id):
            raise ForbiddenError("Pemohon cuti tidak dapat menyetujui atau menolak permohonannya sendiri.")

        if user.role == "PROJECT_MANAGER" and not await self._pm_owns(user, leave.employee_id):
            raise ForbiddenError("PM hanya dapat meninjau cuti karyawan di divisinya.")

        if leave.status in ("APPROVED_BY_HR", "REJECTED", "CANCELLED"):
            raise AppError("ALREADY_DECIDED", "Permohonan cuti ini sudah diputuskan.", status=409)

        is_pm = user.role == "PROJECT_MANAGER"
        if is_pm and leave.status == "APPROVED_BY_PM":
            raise AppError(
                "ALREADY_APPROVED_BY_PM",
                "Permohonan cuti ini sudah disetujui PM dan menunggu persetujuan HR.",
                status=409,
            )

        new_status = "REJECTED" if data.decision == "REJECTED" else ("APPROVED_BY_PM" if is_pm else "APPROVED_BY_HR")

        await self.repo.update_review(
            leave_id=leave_id,
            status=new_status,
            reviewer_id=user.employee_id,
            is_pm=is_pm,
            note=data.note.strip() if data.note else None,
        )

        # Potong kuota cuti tahunan hanya saat disetujui pertama kali (mencegah double deduction)
        # Serta kembalikan saldo (refund) jika persetujuan awal PM kemudian ditolak oleh HR
        if leave.leave_type == "ANNUAL":
            if data.decision == "APPROVED" and leave.status == "PENDING":
                # Pemotongan pertama kali (baik oleh PM maupun langsung oleh HR)
                await self.repo.deduct_balance(leave.employee_id, leave.start_date.year, leave.total_days)
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
        return await self.repo.get_leave(leave_id)

    async def cancel(self, user: CurrentUser, leave_id: UUID) -> Any:
        leave = await self.repo.get_leave(leave_id)
        if leave is None:
            raise NotFoundError("Permohonan cuti")
        if user.employee_id is None or str(user.employee_id) != str(leave.employee_id):
            raise ForbiddenError("Hanya pemohon yang dapat membatalkan permohonan cutinya.")
        if leave.status not in CANCELLABLE_STATUSES:
            raise AppError("NOT_CANCELLABLE", "Permohonan cuti ini sudah tidak dapat dibatalkan.", status=409)

        await self.repo.cancel_leave(leave_id)
        # Kuota sudah dipotong saat disetujui PM; kembalikan bila dibatalkan
        if leave.leave_type == "ANNUAL" and leave.status == "APPROVED_BY_PM":
            await self.repo.deduct_balance(leave.employee_id, leave.start_date.year, -leave.total_days)
        notifier = self._notify()
        await notifier.notify_division_managers(
            leave.employee_id, "LEAVE_CANCELLED",
            f"{await notifier.employee_name(leave.employee_id)} membatalkan pengajuan cuti/izin", "", target="leave",
        )
        return await self.repo.get_leave(leave_id)

    async def _pm_owns(self, user: CurrentUser, employee_id: UUID | str) -> bool:
        pm_id = await self.repo.division_pm_of(employee_id)
        return pm_id is not None and str(pm_id) == str(user.employee_id)

    async def _ensure_can_view(self, user: CurrentUser, employee_id: UUID | str) -> None:
        if user.role in ORG_WIDE_ROLES or str(employee_id) == str(user.employee_id):
            return
        if user.role == "PROJECT_MANAGER" and await self._pm_owns(user, employee_id):
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
        if user.role == "PROJECT_MANAGER":
            pm_id = user.employee_id
        elif user.role not in ORG_WIDE_ROLES:
            if user.employee_id is None:
                return []
            employee_id = UUID(str(user.employee_id))
        return list(
            await self.repo.list_leaves(employee_id=employee_id, status=status, year=year, pm_id=pm_id)
        )

    async def balance(self, user: CurrentUser, employee_id: UUID, year: int) -> Any:
        await self._ensure_can_view(user, employee_id)
        bal = await self.repo.get_or_create_balance(employee_id, year)
        return bal
