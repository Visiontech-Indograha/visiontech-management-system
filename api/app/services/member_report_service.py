"""
app/services/member_report_service.py
Laporan harian berjenjang (alur SK v2 PR2, flowchart SK2-E): anggota menulis & mengirim laporannya ke ketua;
ketua menghimpunnya menjadi laporan harian untuk PM. Juga dokumen A4 laporan harian/mingguan.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PlanStatus
from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.crud.crud_member_report import CRUDMemberReport
from app.crud.crud_org_clock import CRUDOrgClock
from app.services.access_service import PlanAccess, ensure_same_org, require_plan_status
from app.services.notification_service import NotificationService
from app.services.pdf_service import render_report_html


class MemberReportService:
    """Layanan untuk mengelola laporan harian anggota tim di lapangan."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CRUDMemberReport(db)

    async def _me(self, access: PlanAccess) -> str:
        """
        Mendapatkan ID karyawan dari pengguna yang sedang masuk.

        Args:
            access: Akses pengguna terhadap SK saat ini.

        Returns:
            str: ID karyawan yang terhubung dengan akun pengguna.

        Raises:
            ForbiddenError: Jika akun pengguna tidak terhubung ke entitas karyawan manapun.
        """
        # Verifikasi bahwa pengguna merupakan karyawan (bukan akun non-personil)
        employee = await self.repo.employee_of(access.user.user_id)
        if employee is None:
            raise ForbiddenError("Akun Anda belum tertaut ke data karyawan.")
        return employee

    async def _editable(self, access: PlanAccess, day_id: UUID) -> str:
        """
        Memastikan laporan dapat diedit atau diubah pada hari tertentu.

        Args:
            access: Akses pengguna.
            day_id: ID hari laporan.

        Returns:
            str: ID karyawan pengguna.

        Raises:
            AppError/ValidationError: Jika status SK belum berjalan atau tanggal belum tercapai.
        """
        # Laporan hanya bisa dibuat untuk pekerjaan yang berstatus sedang berjalan
        require_plan_status(access, PlanStatus.IN_PROGRESS)
        # Validasi batas waktu: mencegah pengisian laporan untuk tanggal di masa depan
        if not await CRUDOrgClock(self.db).day_reached(day_id):
            raise ValidationError("Laporan hanya dapat diisi pada atau setelah tanggal pelaksanaan.")
        return await self._me(access)

    async def list_for_day(self, day_id: UUID) -> list[Any]:
        """
        Mengambil daftar seluruh laporan anggota pada suatu hari tertentu.
        
        Args:
            day_id: ID hari dari jadwal pekerjaan.
            
        Returns:
            list[Any]: Daftar laporan.
        """
        return await self.repo.list_for_day(day_id)

    async def mine(self, access: PlanAccess, day_id: UUID) -> Any:
        """
        Mengambil draf laporan milik pengguna sendiri pada suatu hari.
        
        Args:
            access: Akses pengguna saat ini.
            day_id: ID hari laporan.
            
        Returns:
            Any: Baris data laporan pengguna.
        """
        return await self.repo.mine(day_id, await self._me(access))

    async def save(self, access: PlanAccess, day_id: UUID, body: str, obstacle: str, file_ids: list[UUID]) -> Any:
        """
        Anggota menyimpan draf laporannya (selama belum dikirim ke ketua).
        
        Args:
            access: Akses pengguna.
            day_id: ID hari laporan.
            body: Isi uraian laporan.
            obstacle: Catatan kendala (jika ada).
            file_ids: Daftar ID berkas bukti pendukung.
            
        Returns:
            Any: Data laporan yang telah diperbarui.
            
        Raises:
            AppError: Jika laporan sudah terkirim (tidak bisa diedit).
        """
        employee = await self._editable(access, day_id)
        # Keamanan: Pastikan berkas yang dilampirkan benar-benar milik organisasi pengguna
        await ensure_same_org(self.db, access.user.organization_id, files=file_ids)
        row = await self.repo.save(day_id, employee, body.strip(), obstacle.strip())
        if row is None:
            raise AppError("INVALID_STATE", "Laporan yang sudah dikirim ke ketua tidak dapat diubah.", status=409)
        await self.repo.replace_evidence(row.id, file_ids)
        return await self.repo.mine(day_id, employee)

    async def send(self, access: PlanAccess, day_id: UUID) -> Any:
        """
        Anggota mengirim laporannya ke ketua tim; ketua mendapat notifikasi.
        
        Args:
            access: Akses pengguna.
            day_id: ID hari.
            
        Returns:
            Any: Data laporan terbaru dengan status terkirim.
            
        Raises:
            AppError: Jika laporan belum disimpan atau sudah pernah dikirim.
            ValidationError: Jika isi laporan terlalu singkat.
        """
        employee = await self._editable(access, day_id)
        current = await self.repo.mine(day_id, employee)
        if current is None:
            raise AppError("INVALID_STATE", "Simpan laporan dulu sebelum mengirim.", status=409)
        if current.status == "SENT":
            raise AppError("INVALID_STATE", "Laporan sudah dikirim ke ketua.", status=409)
        if len(current.body.strip()) < 10:
            raise ValidationError("Uraian laporan minimal 10 karakter.")
        await self.repo.send(day_id, employee)
        day = await self.repo.day_info(day_id)
        await NotificationService(self.db).member_report_sent(access.plan.id, current.full_name, day.work_date)
        return await self.repo.mine(day_id, employee)

    # ── Dokumen A4 laporan (dibaca di web & HP; PDF di server memakai templat yang sama) ─────────
    async def daily_report_html(self, access: PlanAccess, day_id: UUID) -> str:
        """
        Menghasilkan representasi HTML dari dokumen laporan harian tim.
        
        Args:
            access: Akses pengguna.
            day_id: ID hari laporan.
            
        Returns:
            str: String HTML untuk dirender di web, HP, atau dicetak PDF.
            
        Raises:
            NotFoundError: Jika laporan hari tersebut belum ada.
        """
        report = await self.repo.daily_report_doc(day_id)
        if report is None:
            raise NotFoundError("Laporan harian")
        members = await self.repo.list_for_day(day_id)
        header = await self.repo.plan_header(access.plan.id)
        return render_report_html("Laporan harian", header, report,
                                  period=report.work_date, members=[m for m in members if m.status == "SENT"])

    async def weekly_report_html(self, access: PlanAccess, name: str) -> str:
        """
        Menghasilkan representasi HTML dari dokumen laporan mingguan.
        
        Args:
            access: Akses pengguna.
            name: Nama dokumen laporan mingguan.
            
        Returns:
            str: String HTML laporan mingguan.
            
        Raises:
            NotFoundError: Jika laporan mingguan tidak ditemukan.
        """
        report = await self.repo.weekly_report_doc(access.plan.id, name)
        if report is None:
            raise NotFoundError("Laporan mingguan")
        header = await self.repo.plan_header(access.plan.id)
        return render_report_html(report.name, header, report, period=(report.starts_on, report.ends_on), members=[])
