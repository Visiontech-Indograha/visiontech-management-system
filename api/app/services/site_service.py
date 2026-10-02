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
    def __init__(self, repo: CRUDSite) -> None:
        self.repo = repo

    async def list_sites(self, user: CurrentUser, *, for_attendance: bool = False) -> list[Any]:
        """`for_attendance`: hanya lokasi yang sah untuk absen peminta — kantor → lokasi kantor,
        lapangan → lokasi unitnya (sama dengan aturan check-in)."""
        viewer = await self.repo.viewer(user.user_id)
        mode = viewer.attendance_mode if viewer else None
        if for_attendance:
            field = mode == "FIELD"
            unit = viewer.employee_unit_id if viewer and field else None
            return await self.repo.list_visible(user.organization_id, all_sites=False, office=not field,
                                                unit_id=unit)
        if "OPS" in user.roles:
            return await self.repo.list_visible(user.organization_id, all_sites=True, office=True, unit_id=None)
        unit = viewer.pm_unit_id if viewer and viewer.pm_unit_id else (
            viewer.employee_unit_id if viewer and mode == "FIELD" else None)
        return await self.repo.list_visible(user.organization_id, all_sites=False,
                                            office=mode != "FIELD", unit_id=unit)

    async def manageable(self, user: CurrentUser) -> tuple[bool, UUID | None]:
        """(boleh mengelola, unit kelolaan) — dipakai untuk penanda `can_manage` per lokasi."""
        try:
            return True, await self._managed_unit(user)
        except ForbiddenError:
            return False, None

    async def _managed_unit(self, user: CurrentUser) -> UUID | None:
        """Unit lokasi yang boleh dikelola: PM → unitnya; Finance → None (lokasi kantor)."""
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
        unit = await self._managed_unit(user)
        try:
            return await self.repo.insert(user.organization_id, name=name.strip(), address=address,
                                          radius_m=radius_m, lat=lat, lng=lng, unit_id=unit)
        except IntegrityError as exc:
            raise AppError("SITE_INVALID", "Lokasi tidak dapat disimpan. Nama mungkin sudah dipakai.",
                           status=409) from exc

    async def delete_site(self, user: CurrentUser, site_id: UUID) -> None:
        unit = await self._managed_unit(user)
        site = await self.repo.get(site_id, user.organization_id)
        if site is None or site.unit_id != unit:
            raise NotFoundError("Lokasi")  # di luar kelolaan tidak dibocorkan
        await self.repo.archive(site_id)
