"""
app/modules/sites/services/site_service.py
Master kantor (Milestone 2, docs/36): kantor utama & cabang.

- Semua pengguna melihat daftar kantor aktif (target absen kantor, docs/35 §5).
- Kelola (buat/ubah/hapus) butuh izin `manage:sites` (SUPER_ADMIN, OPERATIONAL_MANAGER).
- Tepat satu kantor utama: zona kota & uang makan dihitung dari koordinatnya.
- Kantor yang masih punya karyawan aktif atau kantor utama tidak dapat dihapus.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError, NotFoundError
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.sites.repositories.site_repository import CRUDSite
from app.modules.sites.schemas.site_schema import SiteCreate, SiteUpdate


def _fields(data: SiteCreate | SiteUpdate) -> dict[str, Any]:
    """Skema → parameter kolom office (lokasi dipecah ke lat/lng; alamat kosong → '')."""
    loc = data.location
    return {
        "name": data.name.strip() if data.name else None,
        "address": data.address.strip() if data.address is not None else None,
        "lat": loc.lat if loc else None,
        "lng": loc.lng if loc else None,
        "radius_m": data.radius_m,
        "city_boundary_radius_m": data.city_boundary_radius_m,
        "clock_in_time": data.clock_in_time,
        "clock_out_time": data.clock_out_time,
        "in_city_meal_rate": data.in_city_meal_rate,
        "out_city_meal_rate": data.out_city_meal_rate,
    }


class SiteService:
    """Layanan master kantor."""

    def __init__(self, repo: CRUDSite) -> None:
        self.repo = repo

    @staticmethod
    def can_manage(user: CurrentUser) -> bool:
        return Permission.MANAGE_SITES.value in user.permissions

    async def list_sites(self, user: CurrentUser, *, for_attendance: bool = False) -> list[Any]:
        """Kantor aktif. `for_attendance` dipertahankan untuk klien lama: absen sah di kantor mana pun."""
        return await self.repo.list_active()

    @staticmethod
    def _check_hours(clock_in: Any, clock_out: Any) -> None:
        if clock_in is not None and clock_out is not None and clock_out <= clock_in:
            raise AppError("OFFICE_INVALID", "Jam pulang harus setelah jam masuk.", status=422)

    async def create_site(self, user: CurrentUser, data: SiteCreate) -> Any:
        self._check_hours(data.clock_in_time, data.clock_out_time)
        values = _fields(data)
        values["address"] = values["address"] or ""
        try:
            row = await self.repo.insert(values)
        except IntegrityError as exc:
            raise AppError("OFFICE_INVALID", "Kantor tidak dapat disimpan. Periksa isian lalu coba lagi.",
                           status=409) from exc
        if data.is_main_office:
            await self.repo.set_main(row.id)
            row = await self.repo.get(row.id)
        return row

    async def update_site(self, user: CurrentUser, site_id: UUID, data: SiteUpdate) -> Any:
        current = await self.repo.get(site_id)
        if current is None:
            raise NotFoundError("Kantor")
        self._check_hours(
            data.clock_in_time or current.clock_in_time, data.clock_out_time or current.clock_out_time
        )
        if data.is_main_office is False and current.is_main_office:
            raise AppError(
                "MAIN_OFFICE_REQUIRED",
                "Harus ada satu kantor utama. Tetapkan kantor lain sebagai kantor utama.",
                status=409,
            )
        row = await self.repo.update(site_id, _fields(data))
        if data.is_main_office and not current.is_main_office:
            await self.repo.set_main(site_id)
            row = await self.repo.get(site_id)
        return row

    async def delete_site(self, user: CurrentUser, site_id: UUID) -> None:
        site = await self.repo.get(site_id)
        if site is None:
            raise NotFoundError("Kantor")
        if site.is_main_office:
            raise AppError("MAIN_OFFICE_REQUIRED", "Kantor utama tidak dapat dihapus.", status=409)
        employees = await self.repo.active_employee_count(site_id)
        if employees:
            raise AppError(
                "OFFICE_IN_USE",
                f"Kantor ini masih menjadi kantor {employees} karyawan aktif. Pindahkan karyawan lebih dulu.",
                status=409,
            )
        await self.repo.archive(site_id)
