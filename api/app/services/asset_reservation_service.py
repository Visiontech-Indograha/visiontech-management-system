"""
app/services/asset_reservation_service.py
Reservasi aset (V-27) — padanan `domain.js` RESERVE_ASSET, RELEASE_ASSET, CHECK_ASSET.
Pesan & lepas: petugas aset, atau PM unit/OPS SK tersebut. Periksa: hanya pengemudi yang ditunjuk.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, PlanNeed, check_plan_access
from app.core.enums import PlanStatus
from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError, trigger_rule_error
from app.core.permissions import Permission
from app.repositories.asset_reservation_repo import AssetReservationRepo

RUNNING = (PlanStatus.IN_PROGRESS, PlanStatus.COMPLETION_REVIEW)


def _state(message: str) -> AppError:
    return AppError("INVALID_STATE", message, status=409)


class AssetReservationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AssetReservationRepo(db)

    async def list_assets(self, org_id: str) -> list[Any]:
        """Daftar aset beserta alokasi berjalan & pengajuan pengembalian — dasar tombol kembali/periksa."""
        return await self.repo.list_with_state(org_id)

    async def plan_assets(self, plan_id: UUID) -> list[Any]:
        """Aset yang dipakai SK — akses VIEW SK diperiksa penjaga rute."""
        return await self.repo.plan_assets(plan_id)

    async def return_history(self, org_id: str, asset_id: UUID) -> list[Any]:
        rows = await self.repo.return_history(asset_id, org_id)
        if rows is None:
            raise NotFoundError("Aset")
        return rows

    async def bast(self, org_id: str, return_id: UUID) -> Any:
        """Berita acara serah terima (P6-4): hanya untuk pengembalian yang sudah diperiksa petugas aset."""
        record = await self.repo.return_record(return_id, org_id)
        if record is None:
            raise NotFoundError("Pengembalian aset")
        if record.verified_at is None:
            raise AppError("INVALID_STATE", "Berita acara tersedia setelah pengembalian diperiksa petugas aset.",
                           status=409)
        return record

    async def _manager_of(self, user: CurrentUser, plan_id: UUID | str) -> None:
        """domain.js RESERVE/RELEASE_ASSET: ASSET, OPS, atau PM unit SK itu."""
        if Permission.MANAGE_ASSETS not in user.permissions:
            await check_plan_access(self.db, plan_id, user, PlanNeed.PM_UNIT)

    async def _asset(self, asset_id: UUID) -> Any:
        asset = await self.repo.lock_asset(asset_id)
        if asset is None:
            raise NotFoundError("Aset")
        return asset

    async def reserve(self, user: CurrentUser, asset_id: UUID, plan_id: UUID, driver_id: UUID | None) -> Any:
        await self._manager_of(user, plan_id)
        asset = await self._asset(asset_id)
        plan = await self.repo.plan_for_driver(plan_id, driver_id)
        if plan.status in (PlanStatus.COMPLETED, PlanStatus.CANCELLED):
            raise _state("Pilih work plan yang masih aktif.")
        if asset.status != "AVAILABLE" or await self.repo.active_allocation(asset_id) is not None:
            raise _state("Aset ini sedang dialokasikan dan belum dikembalikan.")
        if asset.kind == "VEHICLE":
            if driver_id is None:
                raise ValidationError("Pilih pengemudi untuk aset kendaraan.")
            if not plan.driver_on_team:
                raise ValidationError("Pengemudi harus bagian dari tim penugasan.")
        else:
            driver_id = None
        try:
            allocation = await self.repo.insert_allocation(asset_id, plan_id, driver_id, user.user_id)
        except IntegrityError as exc:
            # Aturan SIM hidup di trigger asset_allocation_driver (V-11).
            raise (trigger_rule_error(exc) or _state("Aset ini sedang dialokasikan dan belum dikembalikan.")) from None
        in_use = asset.kind != "VEHICLE" and plan.status in RUNNING
        await self.repo.set_asset_status(asset_id, "IN_USE" if in_use else "RESERVED")
        return allocation

    async def release(self, user: CurrentUser, asset_id: UUID, plan_id: UUID) -> str:
        await self._manager_of(user, plan_id)
        asset = await self._asset(asset_id)
        allocation = await self.repo.active_allocation(asset_id)
        if asset.status != "RESERVED" or allocation is None or str(allocation.work_plan_id) != str(plan_id):
            raise _state("Hanya reservasi yang belum dipakai dapat dilepas.")
        await self.repo.free_asset(asset_id, allocation.id, None)
        return "AVAILABLE"

    async def check(self, user: CurrentUser, asset_id: UUID, decision: str, reason: str | None) -> str:
        asset = await self._asset(asset_id)
        allocation = await self.repo.active_allocation(asset_id)
        if allocation is None or asset.kind != "VEHICLE":
            raise _state("Hanya kendaraan yang memerlukan pemeriksaan pengemudi.")
        if str(allocation.driver_employee_id) != await self.repo.employee_of(user.user_id):
            raise ForbiddenError("Hanya pengemudi yang ditunjuk yang dapat melakukan pemeriksaan.")
        if allocation.driver_checked_at is not None:
            raise _state("Kendaraan ini sudah diperiksa.")
        if decision == "ACCEPT":
            await self.repo.mark_checked(allocation.id)
            if allocation.plan_status == PlanStatus.IN_PROGRESS:
                await self.repo.set_asset_status(asset_id, "IN_USE")
                return "IN_USE"
            return str(asset.status)
        if decision != "APPEAL":
            raise ValidationError("Keputusan tidak valid.")
        if not (reason or "").strip():
            raise ValidationError("Alasan banding kelayakan wajib diisi.")
        await self.repo.free_asset(asset_id, allocation.id, f"Banding pengemudi: {(reason or '').strip()}")
        return "AVAILABLE"
