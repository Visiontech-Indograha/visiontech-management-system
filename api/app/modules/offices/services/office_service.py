"""
app/modules/offices/services/office_service.py
Master kantor (Milestone 2, docs/36): kantor utama & cabang.

- Semua pengguna melihat daftar kantor aktif (target absen kantor, docs/35 §5).
- Kelola (buat/ubah/hapus) butuh izin `manage:offices` (SUPER_ADMIN, OPERATIONAL_MANAGER).
- Tepat satu kantor utama: zona kota & uang makan dihitung dari koordinatnya.
- Kantor yang masih punya karyawan aktif atau kantor utama tidak dapat dihapus.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.audit_log import record_audit
from app.core.errors import AppError, NotFoundError
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.offices.repositories.office_repository import CRUDOffice
from app.modules.offices.schemas.office_schema import OfficeCreate, OfficeUpdate


def _fields(data: OfficeCreate | OfficeUpdate) -> dict[str, Any]:
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


_AUDIT_FIELDS = (
    "name", "radius_m", "city_boundary_radius_m", "clock_in_time", "clock_out_time",
    "in_city_meal_rate", "out_city_meal_rate", "is_main_office",
)
_AUDIT_MASKED = ("address",)


class OfficeService:
    """Layanan master kantor."""

    def __init__(self, repo: CRUDOffice) -> None:
        self.repo = repo

    async def _audit(
        self, user: CurrentUser, action: str, office_id: Any, before: Any, after: Any, *, skip_if_empty: bool = False
    ) -> None:
        await record_audit(
            self.repo.db, user, action=action, entity_type="office", entity_id=office_id,
            before=before, after=after, fields=_AUDIT_FIELDS, masked=_AUDIT_MASKED, skip_if_empty=skip_if_empty,
        )

    @staticmethod
    def can_manage(user: CurrentUser) -> bool:
        return Permission.MANAGE_SITES.value in user.permissions

    async def list_offices(self, user: CurrentUser, *, for_attendance: bool = False) -> list[Any]:
        """Kantor aktif. `for_attendance` dipertahankan untuk klien lama: absen sah di kantor mana pun."""
        return await self.repo.list_active()

    @staticmethod
    def _check_hours(clock_in: Any, clock_out: Any) -> None:
        if clock_in is not None and clock_out is not None and clock_out <= clock_in:
            raise AppError("OFFICE_INVALID", "Jam pulang harus setelah jam masuk.", status=422)

    async def create_office(self, user: CurrentUser, data: OfficeCreate) -> Any:
        self._check_hours(data.clock_in_time, data.clock_out_time)
        name_clean = data.name.strip() if data.name else ""
        if await self.repo.name_taken(name_clean):
            raise AppError("DUPLICATE_SITE_NAME", "Nama lokasi kerja sudah digunakan. Gunakan nama lain.", status=409)
        values = _fields(data)
        values["address"] = values["address"] or ""
        try:
            row = await self.repo.insert(values)
        except IntegrityError as exc:
            raise AppError("OFFICE_INVALID", "Kantor tidak dapat disimpan. Periksa isian lalu coba lagi.",
                           status=409) from exc
        # Kantor pertama otomatis jadi kantor utama (absen butuh acuan zona kota; tanpa ini absen gagal 500).
        if data.is_main_office or not await self.repo.has_main():
            await self.repo.set_main(row.id)
            row = await self.repo.get(row.id)
        await self._audit(user, "OFFICE_CREATE", row.id, None, row)
        return row

    async def update_office(self, user: CurrentUser, office_id: UUID, data: OfficeUpdate) -> Any:
        current = await self.repo.get(office_id)
        if current is None:
            raise NotFoundError("Kantor")
        self._check_hours(
            data.clock_in_time or current.clock_in_time, data.clock_out_time or current.clock_out_time
        )
        if data.name is not None:
            name_clean = data.name.strip()
            if await self.repo.name_taken(name_clean, exclude_id=office_id):
                raise AppError(
                    "DUPLICATE_SITE_NAME",
                    "Nama lokasi kerja sudah digunakan. Gunakan nama lain.",
                    status=409,
                )
        if data.is_main_office is False and current.is_main_office:
            raise AppError(
                "MAIN_OFFICE_REQUIRED",
                "Harus ada satu kantor utama. Tetapkan kantor lain sebagai kantor utama.",
                status=409,
            )
        row = await self.repo.update(office_id, _fields(data))
        if data.is_main_office and not current.is_main_office:
            await self.repo.set_main(office_id)
            row = await self.repo.get(office_id)
        await self._audit(user, "OFFICE_UPDATE", office_id, current, row, skip_if_empty=True)
        return row

    async def delete_office(self, user: CurrentUser, office_id: UUID) -> None:
        office = await self.repo.get(office_id)
        if office is None:
            raise NotFoundError("Kantor")
        if office.is_main_office:
            raise AppError("MAIN_OFFICE_REQUIRED", "Kantor utama tidak dapat dihapus.", status=409)
        employees = await self.repo.active_employee_count(office_id)
        if employees:
            raise AppError(
                "OFFICE_IN_USE",
                f"Kantor ini masih menjadi kantor {employees} karyawan aktif. Pindahkan karyawan lebih dulu.",
                status=409,
            )
        await self.repo.archive(office_id)
        await self._audit(user, "OFFICE_DELETE", office_id, office, None)
