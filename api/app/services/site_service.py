"""
app/services/site_service.py
Lokasi kerja (R-33, keputusan pemilik 2026-10-02):
- PM membuat lokasi proyek untuk unitnya — berlaku hanya untuk bawahannya (pekerja lapangan di unit itu).
- Finance membuat lokasi kantor (tanpa unit) — berlaku untuk semua pekerja kantor.
- Yang terlihat: lapangan → lokasi unitnya; kantor → lokasi kantor; PM → kantor + unitnya; OPS → semua.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.security import CurrentUser
from app.crud.crud_site import CRUDSite


class SiteService:
    """
    Layanan untuk mengelola data master lokasi kerja (site).
    PM dapat membuat lokasi proyek; Finance membuat lokasi kantor.
    Hak akses melihat dibedakan antara pekerja lapangan, kantor, PM, dan OPS.
    """
    def __init__(self, repo: CRUDSite) -> None:
        """
        Inisialisasi SiteService.

        Args:
            repo (CRUDSite): Repositori untuk operasi CRUD site.
        """
        self.repo = repo

    async def list_sites(self, user: CurrentUser, *, for_attendance: bool = False) -> list[Any]:
        """
        Menampilkan daftar lokasi yang dapat dilihat oleh pengguna.
        `for_attendance`: jika True, hanya lokasi yang sah untuk absen (kantor untuk staf kantor; lokasi unit + kantor pusat untuk staf lapangan).

        Args:
            user (CurrentUser): Pengguna yang meminta daftar lokasi.
            for_attendance (bool): Filter khusus untuk absensi.

        Returns:
            list[Any]: Daftar lokasi (site) yang terlihat oleh user.
        """
        viewer = await self.repo.viewer(user.user_id)
        mode = viewer.attendance_mode if viewer else None
        if for_attendance:
            field = mode == "FIELD"
            unit = viewer.employee_unit_id if viewer and field else None
            # Staf kantor: lokasi kantor. Pekerja lapangan: lokasi unitnya + kantor pusat (tanpa SK tetap bisa absen).
            return await self.repo.list_visible(user.organization_id, all_sites=False, office=True,
                                                unit_id=unit)
        # OPS dapat melihat semua lokasi
        if "OPS" in user.roles:
            return await self.repo.list_visible(user.organization_id, all_sites=True, office=True, unit_id=None)

        # PM melihat lokasi kantor + unitnya. Staf lapangan: lokasi unitnya + kantor (APK lama memakai daftar ini untuk absen).
        unit = viewer.pm_unit_id if viewer and viewer.pm_unit_id else (
            viewer.employee_unit_id if viewer and mode == "FIELD" else None)
        return await self.repo.list_visible(user.organization_id, all_sites=False,
                                            office=True, unit_id=unit)

    async def manageable(self, user: CurrentUser) -> tuple[bool, UUID | None]:
        """
        Memeriksa apakah pengguna memiliki hak untuk mengelola (membuat/menghapus) lokasi.
        Digunakan untuk penanda `can_manage` per lokasi.

        Args:
            user (CurrentUser): Pengguna.

        Returns:
            tuple[bool, UUID | None]: Status boolean dan ID unit yang dikelola (jika ada).
        """
        try:
            return True, await self._managed_unit(user)
        except ForbiddenError:
            return False, None

    async def _managed_unit(self, user: CurrentUser) -> UUID | None:
        """
        Menentukan unit yang boleh dikelola oleh pengguna: PM -> unitnya; Finance -> None (lokasi kantor).

        Args:
            user (CurrentUser): Pengguna.

        Returns:
            UUID | None: ID unit.
        """
        if "PM" in user.roles:
            viewer = await self.repo.viewer(user.user_id)
            if viewer is None or viewer.pm_unit_id is None:
                raise ForbiddenError("Akun PM ini belum memegang unit, sehingga belum dapat membuat lokasi.")
            unit: UUID = viewer.pm_unit_id
            return unit
        if "FINANCE" in user.roles:
            return None
        raise ForbiddenError("Lokasi kerja hanya dapat dikelola PM (lokasi proyek) atau Finance (lokasi kantor).")

    async def create_site(self, user: CurrentUser, *, name: str, address: str | None, radius_m: int,
                          lat: float, lng: float) -> Any:
        """
        Membuat lokasi kerja baru.

        Args:
            user (CurrentUser): Pengguna pembuat.
            name (str): Nama lokasi.
            address (str | None): Alamat lengkap lokasi.
            radius_m (int): Radius absensi.
            lat (float): Latitude.
            lng (float): Longitude.

        Returns:
            Any: Data lokasi (site) yang baru dibuat.
        """
        unit = await self._managed_unit(user)
        try:
            return await self.repo.insert(user.organization_id, name=name.strip(), address=address,
                                          radius_m=radius_m, lat=lat, lng=lng, unit_id=unit)
        except IntegrityError as exc:
            # Menangkap galat jika nama lokasi sudah digunakan (unique constraint)
            raise AppError("SITE_INVALID", "Lokasi tidak dapat disimpan. Nama mungkin sudah dipakai.",
                           status=409) from exc

    async def delete_site(self, user: CurrentUser, site_id: UUID) -> None:
        """
        Menghapus lokasi kerja (dengan cara diarsipkan/soft delete).

        Args:
            user (CurrentUser): Pengguna yang menghapus.
            site_id (UUID): ID lokasi yang akan dihapus.
        """
        unit = await self._managed_unit(user)
        site = await self.repo.get(site_id, user.organization_id)
        # Tidak membocorkan eksistensi lokasi di luar unit kelolaan (memulangkan 404)
        if site is None or site.unit_id != unit:
            raise NotFoundError("Lokasi")
        await self.repo.archive(site_id)
