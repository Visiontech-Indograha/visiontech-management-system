"""
app/modules/notifications/services/notification_service.py
Notifikasi dalam aplikasi (realtime lewat event SSE; Master Schema V2 tidak menyimpan kotak masuk).

Jadwal harian daily-first: diajukan → PM/OM divisi; disetujui → ketua & anggota tim; ditolak → pembuat jadwal.
Absensi: perlu review → peninjau; diputuskan → karyawannya.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import system_settings
from app.modules.notifications.repositories.notification_repository import NotificationRepository

_MONTH = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")


NO_SITE = "Lokasi belum ditentukan"  # notification.body NOT NULL; jadwal boleh tanpa nama lokasi


class NotificationService:
    """Pengiriman notifikasi realtime ke pihak yang terikat."""

    def __init__(self, db: AsyncSession) -> None:
        self.repo = NotificationRepository(db)

    async def _actor(self) -> str:
        """Nama karyawan pelaku (pengguna yang sedang masuk), dibaca dari konteks sesi `app.user_id`."""
        name = await self.repo.scalar(
            "SELECT e.full_name FROM users u JOIN employee e ON e.employee_id = u.employee_id "
            "WHERE u.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid"
        )
        return str(name) if name else "OM"

    async def _daily(self, daily_plan_id: UUID | str) -> Any:
        return await self.repo.daily_people(daily_plan_id)

    @staticmethod
    def _day_label(p: Any) -> str:
        return f"Jadwal {p.team_name} {p.work_date.day} {_MONTH[p.work_date.month - 1]}"

    async def daily_submitted(self, daily_plan_id: UUID | str) -> None:
        p = await self._daily(daily_plan_id)
        if p:
            await self.repo.insert_many(p.office_id, [p.pm, p.om], "DAILY_SUBMITTED",
                                        f"{self._day_label(p)} menunggu persetujuan", p.site_name or NO_SITE,
                                        daily_plan_id, "plan")

    async def daily_approved(self, daily_plan_id: UUID | str) -> None:
        p = await self._daily(daily_plan_id)
        if p:
            await self.repo.insert_many(p.office_id, [p.leader, *p.members], "DAILY_APPROVED",
                                        f"{self._day_label(p)} disetujui", p.site_name or NO_SITE,
                                        daily_plan_id, "plan")

    async def daily_rejected(self, daily_plan_id: UUID | str, reason: str) -> None:
        p = await self._daily(daily_plan_id)
        if p:
            await self.repo.insert_many(p.office_id, [p.creator], "DAILY_REJECTED",
                                        f"{await self._actor()} mengembalikan {self._day_label(p)}", reason,
                                        daily_plan_id, "plan")

    async def employee_name(self, employee_id: UUID | str) -> str:
        return await self.repo.employee_name(employee_id)

    async def notify_division_managers(
        self, employee_id: UUID | str, kind: str, title: str, body: str = "", *,
        target: str | None = None,
        roles: Iterable[str] = ("PROJECT_MANAGER", "OPERATIONAL_MANAGER"),
    ) -> None:
        """Notifikasi ke PM/OM yang tercatat di divisi karyawan itu (division.pm_id / om_id)."""
        where = await self.repo.employee_division(employee_id)
        if where is None or where.division_id is None:
            return
        users = await self.repo.division_manager_user_ids(where.division_id, roles)
        await self.repo.insert_for_users(users, kind, title, body, None, target)

    async def notify_employees(
        self, employee_ids: Iterable[str | UUID | None], kind: str, title: str, body: str = "",
        *, target: str | None = None, plan_id: UUID | str | None = None,
    ) -> None:
        """Notifikasi ke karyawan tertentu (disimpan di kotak masuk + realtime)."""
        users = await self.repo.user_ids_for_employees(str(e) for e in employee_ids if e)
        await self.repo.insert_for_users(users, kind, title, body, plan_id, target)

    async def notify_users(
        self, user_ids: Iterable[str], kind: str, title: str, body: str = "", *, target: str | None = None,
    ) -> None:
        """Notifikasi ke akun tertentu (user_id), mis. dari pekerjaan terjadwal."""
        await self.repo.insert_for_users(user_ids, kind, title, body, None, target)

    async def notify_roles(
        self, roles: Iterable[str], kind: str, title: str, body: str = "",
        *, office_id: UUID | str | None = None, division_id: UUID | str | None = None,
        target: str | None = None, plan_id: UUID | str | None = None, exclude_user_id: str | None = None,
    ) -> None:
        """Notifikasi ke semua akun berperan tertentu (opsional per kantor/divisi), selain pelaku."""
        users = await self.repo.user_ids_with_role(roles, office_id, division_id)
        await self.repo.insert_for_users(
            [u for u in users if u != exclude_user_id], kind, title, body, plan_id, target
        )

    async def notify_hr_of_office(
        self, office_id: UUID | str | None, kind: str, title: str, body: str = "", *, target: str | None = None,
    ) -> None:
        """Notifikasi ke HR/GA. Flag ROLE_ASSIGNMENT_ENABLED mati = semua ADMIN_HR_GA (perilaku lama); hidup =
        hanya HR yang cakupannya meliputi `office_id` (kantor sendiri + penugasan HR)."""
        if not system_settings.role_assignment_enabled():
            await self.notify_roles(["ADMIN_HR_GA"], kind, title, body, target=target)
            return
        users = await self.repo.hr_user_ids_for_office(office_id)
        await self.repo.insert_for_users(users, kind, title, body, None, target)

    async def list_for(self, user_id: str, unread_only: bool = False, limit: int = 50) -> list[Any]:
        """
        Mengambil daftar notifikasi untuk pengguna tertentu.

        Args:
            user_id (str): ID pengguna.
            unread_only (bool): Jika True, hanya ambil notifikasi yang belum dibaca.
            limit (int): Batas jumlah notifikasi (default 50).

        Returns:
            list[Any]: Daftar objek notifikasi.
        """
        return await self.repo.list_for(user_id, unread_only, min(max(limit, 1), 100))

    async def unread_count(self, user_id: str) -> int:
        """
        Menghitung jumlah notifikasi yang belum dibaca oleh pengguna.

        Args:
            user_id (str): ID pengguna.

        Returns:
            int: Jumlah notifikasi belum dibaca.
        """
        return await self.repo.unread_count(user_id)

    async def mark_read(self, user_id: str, notification_id: UUID | None) -> int:
        """
        Menandai notifikasi sebagai telah dibaca.

        Args:
            user_id (str): ID pengguna.
            notification_id (UUID | None): ID notifikasi tunggal (atau None untuk semua).

        Returns:
            int: Jumlah baris yang diperbarui.
        """
        return await self.repo.mark_read(user_id, notification_id)

    async def attendance_flagged(self, org_id: str, reviewers: Iterable[str], title: str) -> None:
        """Absen Perlu review (mis. "Absen pulang Andi di luar radius (420 m)") → PM/peninjau berwenang."""
        await self.repo.insert_many(org_id, reviewers, "ATTENDANCE_FLAGGED", title, "Periksa di menu Absensi.", None)

    async def attendance_decided(self, org_id: str, employee_id: str, approved: bool, note: str) -> None:
        """Keputusan peninjau atas absensi → karyawannya."""
        verb = "menyetujui" if approved else "menolak"
        await self.repo.insert_many(
            org_id,
            [employee_id],
            "ATTENDANCE_DECIDED",
            f"{await self._actor()} {verb} absensi Anda",
            f"Catatan: {note}",
            None,
        )

    async def attendance_early_leave(
        self, org_id: str, reviewers: Iterable[str], employee_name: str, detail: str
    ) -> None:
        """Pemberitahuan kepada peninjau/PM saat karyawan pulang lebih awal."""
        await self.repo.insert_many(
            org_id,
            reviewers,
            "ATTENDANCE_EARLY_LEAVE",
            f"Pulang Cepat: {employee_name}",
            f"{employee_name} melakukan absen pulang lebih awal ({detail}).",
            None,
        )

    async def attendance_encouragement(self, org_id: str, employee_id: str, message: str) -> None:
        """Pesan penyemangat untuk karyawan yang menyelesaikan waktu kerja penuh."""
        await self.repo.insert_many(
            org_id,
            [employee_id],
            "ATTENDANCE_ENCOURAGEMENT",
            "Terima Kasih Atas Kerja Kerasmu Hari Ini! 🌟",
            message,
            None,
        )

    async def attendance_auto_checkout_bulk(self, org_id: str, employee_ids: Iterable[str]) -> None:
        """Pemberitahuan bahwa absensi ditutup otomatis oleh sistem pada pukul 19:00."""
        await self.repo.insert_many(
            org_id,
            employee_ids,
            "ATTENDANCE_AUTO_CHECKOUT",
            "Absensi Ditutup Otomatis (19:00)",
            "Sesi absensi Anda hari ini telah ditutup otomatis oleh sistem pada pukul 19:00 dengan keterangan "
            "'Lupa absen pulang'.",
            None,
        )
