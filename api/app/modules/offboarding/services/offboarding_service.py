"""
app/modules/offboarding/services/offboarding_service.py
Offboarding PKWT & clearance aset (Milestone 9, docs/35 §7).

1. HR membuat offboarding → semua pinjaman aset yang belum kembali menjadi item clearance; karyawan `in_process`
   (tidak bisa meminjam aset baru). Ketua tim aktif / PM-OM divisi harus diserahterimakan dulu.
2. HR/GA memverifikasi tiap barang (GOOD/DAMAGED/LOST + foto serah terima) → pinjaman ditutup & status aset diperbarui
   lewat modul aset. Semua terverifikasi → `is_all_assets_returned`, status SUBMITTED (sebelumnya CLEARANCE_PENDING).
3. Persetujuan PM/OM divisi karyawan & HR (urutan bebas, keduanya wajib, hanya setelah clearance lengkap).
4. Keduanya setuju dan tanggal efektif tiba → COMPLETED: karyawan `offboarded`, keanggotaan tim berakhir, akun
   nonaktif & sesi dicabut. Tanggal efektif di masa depan → APPROVED, diselesaikan penjadwal `complete-due`.
Pengelola melihat semua; PM/OM hanya karyawan divisinya. Tak terlihat → 404.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.core.time import jakarta_now
from app.modules.assets.services.asset_service import AssetService
from app.modules.offboarding.repositories.offboarding_repository import OffboardingRepository
from app.modules.offboarding.schemas.offboarding_schema import ClearanceItemVerify, OffboardingCreate

ASSET_STATUS = {"GOOD": "ready", "DAMAGED": "damaged", "LOST": "lost"}
CLEARANCE_OPEN = ("CLEARANCE_PENDING", "SUBMITTED")


def _manages_all(user: CurrentUser) -> bool:
    return user.role == "SUPER_ADMIN" or Permission.MANAGE_OFFBOARDING.value in user.permissions


class OffboardingService:
    def __init__(self, repo: OffboardingRepository, assets: AssetService) -> None:
        self.repo = repo
        self.assets = assets

    # ── Baca ─────────────────────────────────────────────────────────────────
    async def _my_division(self, user: CurrentUser) -> str | None:
        """None = semua divisi (HR/admin/OM); PM hanya divisinya."""
        if _manages_all(user) or user.role == "OPERATIONAL_MANAGER":
            return None
        if not user.employee_id:
            raise ForbiddenError("Akun ini belum tertaut ke data karyawan.")
        division = await self.repo.scalar(
            "SELECT division_id FROM division WHERE pm_id = CAST(:e AS uuid) AND delete_at IS NULL LIMIT 1",
            {"e": user.employee_id},
        )
        return str(division) if division else "00000000-0000-0000-0000-000000000000"

    async def list_all(self, user: CurrentUser, status: str | None) -> list[Any]:
        return await self.repo.list_all(status=status, division_id=await self._my_division(user))

    async def _visible(self, user: CurrentUser, offboarding_id: UUID, *, for_update: bool = False) -> Any:
        record = await self.repo.get(offboarding_id, for_update=for_update)
        division = await self._my_division(user)
        if record is None or (division is not None and str(record.division_id) != division):
            raise NotFoundError("Data offboarding")
        return record

    async def detail(self, user: CurrentUser, offboarding_id: UUID) -> dict[str, Any]:
        record = await self._visible(user, offboarding_id)
        return {**dict(record._mapping), "clearance_items": [dict(i._mapping) for i in
                                                              await self.repo.items(offboarding_id)]}

    async def pkwt_expiring(self, user: CurrentUser, days: int) -> list[Any]:
        until = jakarta_now().date() + timedelta(days=days)
        return await self.repo.pkwt_expiring(until, await self._my_division(user))

    # ── Proses ───────────────────────────────────────────────────────────────
    async def create(self, data: OffboardingCreate) -> dict[str, Any]:
        employee = await self.repo.employee_for_offboarding(data.employee_id)
        if employee is None:
            raise NotFoundError("Karyawan")
        if employee.offboarding_status != "active" or await self.repo.open_for_employee(data.employee_id):
            raise AppError("ALREADY_OFFBOARDING", "Karyawan ini sudah dalam proses atau selesai offboarding.",
                           status=409)
        effective = data.effective_date
        if effective is None:
            if data.reason_type != "PKWT_EXPIRED" or employee.pkwt_end_date is None:
                raise ValidationError("Isi tanggal efektif (otomatis hanya untuk PKWT berakhir yang tanggalnya ada).")
            effective = employee.pkwt_end_date
        if effective < employee.join_date:
            raise ValidationError("Tanggal efektif tidak boleh sebelum tanggal bergabung.")
        if employee.leads_teams or employee.manages_divisions:
            held = "; ".join(x for x in (
                f"ketua tim {employee.leads_teams}" if employee.leads_teams else "",
                f"PM/OM divisi {employee.manages_divisions}" if employee.manages_divisions else "") if x)
            raise AppError("HANDOVER_REQUIRED", f"Serahterimakan jabatan dulu: {held}.", status=409)
        offboarding_id = await self.repo.create(employee_id=data.employee_id, reason=data.reason_type.value,
                                                effective_date=effective, notes=(data.notes or "").strip() or None)
        record = await self.repo.get(offboarding_id)
        return {**dict(record._mapping), "clearance_items": [dict(i._mapping) for i in
                                                              await self.repo.items(offboarding_id)]}

    async def verify_item(self, user: CurrentUser, clearance_item_id: UUID, data: ClearanceItemVerify) -> Any:
        item = await self.repo.item_for_update(clearance_item_id)
        if item is None:
            raise NotFoundError("Item clearance")
        if item.status not in CLEARANCE_OPEN:
            raise AppError("INVALID_STATE", "Offboarding ini tidak lagi menerima verifikasi barang.", status=409)
        if item.verified_at is not None:
            raise AppError("ALREADY_VERIFIED", "Barang ini sudah diverifikasi.", status=409)
        if not user.employee_id:
            raise ForbiddenError("Akun ini belum tertaut ke data karyawan.")
        photo = None
        if data.handover_file_id is not None:
            photo = await self.repo.file_key(data.handover_file_id)
            if photo is None:
                raise ValidationError("Foto serah terima belum diunggah atau bukan gambar.")
        if item.returned_at is None:  # sudah dikembalikan lewat menu aset → cukup catat kondisinya
            await self.assets.return_loan(item.assignment_id, ASSET_STATUS[data.return_condition])
        await self.repo.verify_item(clearance_item_id, data.return_condition, photo, user.employee_id)
        await self.repo.refresh_clearance(item.offboarding_id)
        return await self.detail(user, item.offboarding_id)

    async def approve(self, user: CurrentUser, offboarding_id: UUID, approval_type: str) -> dict[str, Any]:
        record = await self._visible(user, offboarding_id, for_update=True)
        if record.status not in ("SUBMITTED", "APPROVED") or not record.is_all_assets_returned:
            raise AppError("CLEARANCE_INCOMPLETE",
                           "Persetujuan baru bisa setelah semua barang pinjaman diverifikasi.", status=409)
        if not user.employee_id:
            raise ForbiddenError("Akun ini belum tertaut ke data karyawan.")
        if user.employee_id == str(record.employee_id):
            raise ForbiddenError("Tidak bisa menyetujui offboarding diri sendiri.")
        as_pm = approval_type == "PM"
        if as_pm:
            managers = await self.repo.division_managers(record.division_id)
            allowed = user.role == "SUPER_ADMIN" or (
                managers is not None and user.employee_id in (str(managers.pm_id), str(managers.om_id))
            ) or (record.division_id is None and user.role == "OPERATIONAL_MANAGER")
            if not allowed:
                raise ForbiddenError("Persetujuan PM hanya oleh PM/OM divisi karyawan.")
            if record.approved_by_pm_id is not None:
                raise AppError("ALREADY_APPROVED", "PM sudah menyetujui.", status=409)
        else:
            if not _manages_all(user):
                raise ForbiddenError("Persetujuan HR hanya oleh pengelola offboarding (HR).")
            if record.approved_by_hr_id is not None:
                raise AppError("ALREADY_APPROVED", "HR sudah menyetujui.", status=409)
        await self.repo.approve(offboarding_id, as_pm=as_pm, approver_id=user.employee_id)
        updated = await self.repo.get(offboarding_id)
        if updated.status == "APPROVED" and updated.effective_date <= jakarta_now().date():
            await self.repo.finalize(offboarding_id, updated.employee_id)
        return await self.detail(user, offboarding_id)

    async def complete_due(self) -> int:
        """Penjadwal: selesaikan offboarding yang sudah disetujui dan tanggal efektifnya tiba."""
        due = await self.repo.due_for_completion(jakarta_now().date())
        for row in due:
            await self.repo.finalize(row.offboarding_id, row.employee_id)
        return len(due)

    async def cancel(self, user: CurrentUser, offboarding_id: UUID, reason: str) -> None:
        record = await self._visible(user, offboarding_id, for_update=True)
        if record.status == "COMPLETED":
            raise AppError("INVALID_STATE", "Offboarding yang sudah selesai tidak bisa dibatalkan.", status=409)
        await self.repo.cancel(offboarding_id, record.employee_id, reason.strip())
