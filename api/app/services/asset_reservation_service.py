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

from app.core.enums import PlanStatus
from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError, trigger_rule_error
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.crud.crud_asset_reservation import CRUDAssetReservation
from app.services.access_service import PlanNeed, check_plan_access

RUNNING = (PlanStatus.IN_PROGRESS, PlanStatus.COMPLETION_REVIEW)


def _state(message: str) -> AppError:
    return AppError("INVALID_STATE", message, status=409)


class AssetReservationService:
    """Layanan untuk mengelola proses reservasi, peminjaman, dan pengembalian aset proyek."""
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CRUDAssetReservation(db)

    async def list_assets(self, org_id: str) -> list[Any]:
        """
        Daftar aset beserta alokasi berjalan & pengajuan pengembalian — dasar tombol kembali/periksa.
        
        Args:
            org_id: ID organisasi.
            
        Returns:
            Daftar aset.
        """
        return await self.repo.list_with_state(org_id)

    async def plan_assets(self, plan_id: UUID) -> list[Any]:
        """
        Mendapatkan aset yang dipakai SK tertentu. Akses VIEW SK diperiksa penjaga rute.
        
        Args:
            plan_id: ID work plan.
            
        Returns:
            Daftar aset yang digunakan pada SK tersebut.
        """
        return await self.repo.plan_assets(plan_id)

    async def return_history(self, org_id: str, asset_id: UUID) -> list[Any]:
        """
        Mendapatkan riwayat pengembalian untuk suatu aset.
        """
        rows = await self.repo.return_history(asset_id, org_id)
        if rows is None:
            raise NotFoundError("Aset")
        return rows

    async def bast(self, org_id: str, return_id: UUID) -> Any:
        """
        Berita acara serah terima (P6-4): hanya untuk pengembalian yang sudah diperiksa petugas aset.
        
        Args:
            org_id: ID organisasi.
            return_id: ID pengembalian.
        """
        record = await self.repo.return_record(return_id, org_id)
        if record is None:
            raise NotFoundError("Pengembalian aset")
        # Dokumen BAST hanya dapat dicetak apabila pengembalian fisik telah divalidasi oleh petugas aset.
        if record.verified_at is None:
            raise AppError("INVALID_STATE", "Berita acara tersedia setelah pengembalian diperiksa petugas aset.",
                           status=409)
        return record

    async def _manager_of(self, user: CurrentUser, plan_id: UUID | str) -> None:
        """
        domain.js RESERVE/RELEASE_ASSET: ASSET, OPS, atau PM unit SK itu.
        Memverifikasi kewenangan pengguna untuk mengelola aset pada SK tertentu.
        """
        if Permission.MANAGE_ASSETS not in user.permissions:
            # Jika bukan petugas aset, periksa apakah pengguna adalah PM dari unit SK tersebut.
            await check_plan_access(self.db, plan_id, user, PlanNeed.PM_UNIT)

    async def _asset(self, asset_id: UUID) -> Any:
        """
        Mengunci dan memuat data aset (mencegah modifikasi konkuren/race conditions).
        """
        asset = await self.repo.lock_asset(asset_id)
        if asset is None:
            raise NotFoundError("Aset")
        return asset

    async def reserve(self, user: CurrentUser, asset_id: UUID, plan_id: UUID, driver_id: UUID | None) -> Any:
        """
        Merereservasi aset untuk digunakan pada suatu SK.
        
        Args:
            user: Pengguna yang melakukan reservasi.
            asset_id: ID aset.
            plan_id: ID SK/Work plan.
            driver_id: ID pengemudi (wajib jika aset kendaraan).
            
        Returns:
            Data alokasi aset.
        """
        await self._manager_of(user, plan_id)
        asset = await self._asset(asset_id)
        plan = await self.repo.plan_for_driver(plan_id, driver_id)
        
        # Aset hanya bisa dipinjamkan pada SK yang sedang berjalan/belum selesai.
        if plan.status in (PlanStatus.COMPLETED, PlanStatus.CANCELLED):
            raise _state("Pilih work plan yang masih aktif.")
        # Mencegah bentrokan reservasi jika aset sedang dipakai orang lain.
        if asset.status != "AVAILABLE" or await self.repo.active_allocation(asset_id) is not None:
            raise _state("Aset ini sedang dialokasikan dan belum dikembalikan.")
            
        if asset.kind == "VEHICLE":
            if driver_id is None:
                raise ValidationError("Pilih pengemudi untuk aset kendaraan.")
            # Validasi pengemudi harus merupakan bagian dari tim SK yang ditugaskan.
            if not plan.driver_on_team:
                raise ValidationError("Pengemudi harus bagian dari tim penugasan.")
        else:
            driver_id = None
            
        try:
            allocation = await self.repo.insert_allocation(asset_id, plan_id, driver_id, user.user_id)
        except IntegrityError as exc:
            # Aturan SIM hidup di trigger asset_allocation_driver (V-11). Trigger memeriksa masa berlaku SIM pengemudi.
            raise (trigger_rule_error(exc) or _state("Aset ini sedang dialokasikan dan belum dikembalikan.")) from None
            
        in_use = asset.kind != "VEHICLE" and plan.status in RUNNING
        await self.repo.set_asset_status(asset_id, "IN_USE" if in_use else "RESERVED")
        return allocation

    async def release(self, user: CurrentUser, asset_id: UUID, plan_id: UUID) -> str:
        """
        Melepaskan aset yang sudah direvservasi tetapi belum dipakai/diterima.
        """
        await self._manager_of(user, plan_id)
        asset = await self._asset(asset_id)
        allocation = await self.repo.active_allocation(asset_id)
        
        # Memastikan hanya reservasi yang masih dalam status tertunda yang dapat dibatalkan pelepasannya.
        if asset.status != "RESERVED" or allocation is None or str(allocation.work_plan_id) != str(plan_id):
            raise _state("Hanya reservasi yang belum dipakai dapat dilepas.")
            
        await self.repo.free_asset(asset_id, allocation.id, None)
        return "AVAILABLE"

    async def check(self, user: CurrentUser, asset_id: UUID, decision: str, reason: str | None) -> str:
        """
        Melakukan pemeriksaan (cek kelayakan) oleh pengemudi sebelum membawa kendaraan.
        """
        asset = await self._asset(asset_id)
        allocation = await self.repo.active_allocation(asset_id)
        
        if allocation is None or asset.kind != "VEHICLE":
            raise _state("Hanya kendaraan yang memerlukan pemeriksaan pengemudi.")
        # Hanya pengemudi yang dialokasikan yang boleh menyatakan kendaraan layak atau tidak.
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
            
        # Jika kendaraan tidak layak, aset dilepaskan (free) dengan alasan banding dari pengemudi.
        await self.repo.free_asset(asset_id, allocation.id, f"Banding pengemudi: {(reason or '').strip()}")
        return "AVAILABLE"
