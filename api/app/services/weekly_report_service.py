"""
app/services/weekly_report_service.py
Laporan mingguan (V-25) — padanan `domain.js` SAVE_WEEKLY, SUBMIT_WEEKLY, REVIEW_WEEKLY.
Ketua menurut SK mengisi & menyerahkan; PM unit/OPS memeriksa. Kewenangan dicek penjaga V-07 di router.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PlanStatus
from app.core.errors import AppError, NotFoundError, ValidationError
from app.crud.crud_weekly_report import CRUDWeeklyReport
from app.services.access_service import PlanAccess, require_plan_status
from app.services.notification_service import NotificationService

EDITABLE = ("DRAFT", "CHANGES_REQUESTED")


def _state(message: str) -> AppError:
    return AppError("INVALID_STATE", message, status=409)


class WeeklyReportService:
    """
    Layanan untuk mengelola laporan mingguan dari tim SK.
    Mengontrol proses pengisian, penyerahan, dan peninjauan laporan mingguan.
    """
    def __init__(self, db: AsyncSession) -> None:
        """
        Inisialisasi WeeklyReportService.

        Args:
            db (AsyncSession): Sesi database asinkron.
        """
        self.repo = CRUDWeeklyReport(db)

    async def list_weeks(self, access: PlanAccess) -> list[Any]:
        """
        Mendapatkan daftar semua minggu kerja untuk sebuah SK.

        Args:
            access (PlanAccess): Akses terhadap SK.

        Returns:
            list[Any]: Daftar minggu kerja.
        """
        return await self.repo.list_weeks(access.plan.id)

    async def _week(self, access: PlanAccess, week: int) -> Any:
        """
        Fungsi pembantu (helper) untuk mengambil data satu minggu spesifik dan memvalidasi eksistensinya.

        Args:
            access (PlanAccess): Akses terhadap SK.
            week (int): Urutan minggu.

        Returns:
            Any: Data minggu yang diminta.
        """
        row = await self.repo.get_week(access.plan.id, week)
        if row is None:
            raise NotFoundError("Minggu")
        return row

    async def _editable_week(self, access: PlanAccess, week: int) -> Any:
        """
        Memastikan bahwa minggu yang diminta dapat diubah (diedit) dan SK dalam status IN_PROGRESS.

        Args:
            access (PlanAccess): Akses terhadap SK.
            week (int): Urutan minggu.

        Returns:
            Any: Data minggu jika valid untuk diedit.
        """
        require_plan_status(access, PlanStatus.IN_PROGRESS)
        row = await self._week(access, week)
        # Hanya minggu dengan status DRAFT atau CHANGES_REQUESTED yang boleh diubah.
        if row.status not in EDITABLE:
            raise _state("Laporan mingguan sudah diserahkan.")
        return row

    async def save_weekly(self, access: PlanAccess, week: int, body: str, obstacle: str) -> Any:
        """
        Menyimpan draf laporan mingguan (belum disubmit ke peninjau).

        Args:
            access (PlanAccess): Akses terhadap SK.
            week (int): Urutan minggu.
            body (str): Isi / deskripsi laporan mingguan.
            obstacle (str): Kendala mingguan yang dialami.

        Returns:
            Any: Data laporan minggu setelah disimpan.
        """
        row = await self._editable_week(access, week)
        await self.repo.save(access.plan.id, row, body.strip(), obstacle.strip())
        return await self._week(access, week)

    async def submit_weekly(self, access: PlanAccess, week: int) -> Any:
        """
        Menyerahkan (submit) laporan mingguan ke peninjau (PM unit/OPS).
        Memerlukan validasi bahwa semua laporan harian di minggu tersebut sudah disetujui, dan field wajib terisi.

        Args:
            access (PlanAccess): Akses terhadap SK.
            week (int): Urutan minggu.

        Returns:
            Any: Data minggu setelah status berubah.
        """
        row = await self._editable_week(access, week)
        # Validasi: semua laporan harian dalam minggu ini sudah di-approve
        if not row.days_approved:
            raise _state("Semua laporan harian dalam minggu ini harus disetujui terlebih dahulu.")
        # Validasi: isi/deskripsi harus memadai (lebih dari 10 karakter)
        if len(row.body) <= 10:
            raise ValidationError("Laporan mingguan wajib diisi.")
        # Validasi: harus mengisi kolom kendala, minimal menyatakan "Tidak ada"
        if not row.obstacle:
            raise ValidationError('Ringkasan kendala mingguan wajib diisi (isi "Tidak ada" jika lancar).')

        # Mengeksekusi perubahan status menjadi submitted di database
        await self.repo.submit(access.plan.id, row.name, access.user.user_id)
        # Memicu notifikasi setelah laporan diserahkan
        await NotificationService(self.repo.db).report_submitted(access.plan.id, row.name,
                                                                 row.status == "CHANGES_REQUESTED")
        return await self._week(access, week)

    async def review_weekly(self, access: PlanAccess, week: int, decision: str, note: str | None) -> Any:
        """
        Peninjauan (review) atas laporan mingguan oleh PM unit atau OPS.
        Dapat disetujui (APPROVE) atau dikembalikan dengan revisi (RETURN).

        Args:
            access (PlanAccess): Akses terhadap SK.
            week (int): Urutan minggu.
            decision (str): Keputusan ("APPROVE" atau "RETURN").
            note (str | None): Catatan (wajib diisi jika dikembalikan).

        Returns:
            Any: Data minggu yang telah di-review.
        """
        # Status SK harus IN_PROGRESS atau sedang direview untuk penutupan
        require_plan_status(access, PlanStatus.IN_PROGRESS, PlanStatus.COMPLETION_REVIEW)
        if decision not in ("APPROVE", "RETURN"):
            raise ValidationError("Pilihan keputusan tidak dikenali. Muat ulang, lalu pilih lagi.")
        clean_note = (note or "").strip()
        # Jika direturn (ditolak), wajib memberi catatan alasan penolakan
        if decision == "RETURN" and not clean_note:
            raise ValidationError("Catatan revisi wajib diisi.")

        row = await self._week(access, week)
        status = "APPROVED" if decision == "APPROVE" else "CHANGES_REQUESTED"
        # Memastikan statusnya benar menunggu review di database
        if await self.repo.review(access.plan.id, row.name, status, clean_note or None, access.user.user_id) is None:
            raise _state("Laporan mingguan belum menunggu pemeriksaan.")

        # Mengirim notifikasi terkait hasil review kepada tim
        await NotificationService(self.repo.db).report_reviewed(access.plan.id, row.name, decision == "APPROVE",
                                                                clean_note or None)
        return await self._week(access, week)
