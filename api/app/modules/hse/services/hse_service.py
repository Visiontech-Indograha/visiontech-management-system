"""
api/app/modules/hse/services/hse_service.py

Layanan logika bisnis untuk domain HSE (Health, Safety & Environment):
- Pengelolaan kampanye & materi keselamatan kerja
- Gerbang popup wajib baca (non-skippable gate)
- Audit jejak pembaca materi keselamatan
- Inspeksi keselamatan kendaraan kerja lapangan
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import CurrentUser
from app.modules.hse.repositories.hse_campaign_repository import HseCampaignRepository
from app.modules.hse.repositories.vehicle_inspection_repository import VehicleInspectionRepository
from app.modules.hse.schemas.hse_schema import (
    HseAcknowledgeCreate,
    HseCampaignAuditStats,
    HseCampaignCreate,
    HseCampaignResponse,
    HseCampaignUpdate,
    HseReaderItem,
    VehicleInspectionCreate,
    VehicleInspectionResponse,
    VehicleInspectionVerify,
)


class HseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.campaign_repo = HseCampaignRepository(db)
        self.inspection_repo = VehicleInspectionRepository(db)

    # ================= Kampanye K3 =================
    async def create_campaign(
        self,
        data: HseCampaignCreate,
        current_user: CurrentUser,
    ) -> HseCampaignResponse:
        if data.end_date < data.start_date:
            raise AppError("INVALID_DATE_RANGE", "Tanggal akhir kampanye tidak boleh sebelum tanggal awal.", status=400)

        created = await self.campaign_repo.create(data, UUID(str(current_user.user_id)))
        full_data = await self.campaign_repo.get_by_id(UUID(str(created["campaign_id"])))
        if not full_data:
            raise AppError("CREATION_FAILED", "Gagal mengambil data kampanye setelah pembuatan.", status=500)
        return HseCampaignResponse.model_validate(full_data)

    async def get_campaign(self, campaign_id: UUID) -> HseCampaignResponse:
        campaign = await self.campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise AppError("NOT_FOUND", "Kampanye K3 tidak ditemukan.", status=404)
        return HseCampaignResponse.model_validate(campaign)

    async def list_campaigns(
        self,
        limit: int = 50,
        offset: int = 0,
        is_active: bool | None = None,
        target_audience: str | None = None,
    ) -> list[HseCampaignResponse]:
        items = await self.campaign_repo.list_campaigns(
            limit=limit,
            offset=offset,
            is_active=is_active,
            target_audience=target_audience,
        )
        return [HseCampaignResponse.model_validate(item) for item in items]

    async def update_campaign(
        self,
        campaign_id: UUID,
        data: HseCampaignUpdate,
    ) -> HseCampaignResponse:
        existing = await self.campaign_repo.get_by_id(campaign_id)
        if not existing:
            raise AppError("NOT_FOUND", "Kampanye K3 tidak ditemukan.", status=404)

        if data.start_date and data.end_date and data.end_date < data.start_date:
            raise AppError("INVALID_DATE_RANGE", "Tanggal akhir tidak boleh sebelum tanggal awal.", status=400)

        updated = await self.campaign_repo.update(campaign_id, data)
        if not updated:
            raise AppError("UPDATE_FAILED", "Gagal memperbarui kampanye K3.", status=500)
        return HseCampaignResponse.model_validate(updated)

    async def delete_campaign(self, campaign_id: UUID) -> bool:
        existing = await self.campaign_repo.get_by_id(campaign_id)
        if not existing:
            raise AppError("NOT_FOUND", "Kampanye K3 tidak ditemukan.", status=404)
        return await self.campaign_repo.delete(campaign_id)

    # ================= Gerbang Popup Wajib Baca (Gate) =================
    async def get_active_popup(self, current_user: CurrentUser) -> dict[str, Any] | None:
        """
        Mengambil popup kampanye K3 wajib yang belum disetujui (unacknowledged) untuk pengguna saat ini.
        Jika tidak ada, mengembalikan None.
        """
        user_uuid = UUID(str(current_user.user_id))
        system_role = str(current_user.role)
        return await self.campaign_repo.get_active_popup_for_user(user_uuid, system_role)

    async def acknowledge_campaign(
        self,
        campaign_id: UUID,
        current_user: CurrentUser,
        data: HseAcknowledgeCreate,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        campaign = await self.campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise AppError("NOT_FOUND", "Kampanye K3 tidak ditemukan.", status=404)

        user_uuid = UUID(str(current_user.user_id))
        result = await self.campaign_repo.record_acknowledgment(
            campaign_id=campaign_id,
            user_id=user_uuid,
            data=data,
            ip_address=ip_address,
        )
        return result

    async def get_campaign_audit_stats(self, campaign_id: UUID) -> HseCampaignAuditStats:
        campaign = await self.campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise AppError("NOT_FOUND", "Kampanye K3 tidak ditemukan.", status=404)

        raw_readers = await self.campaign_repo.list_readers_by_campaign(campaign_id)
        readers = [HseReaderItem.model_validate(r) for r in raw_readers]

        return HseCampaignAuditStats(
            campaign_id=campaign_id,
            title=str(campaign["title"]),
            target_audience=str(campaign["target_audience"]),
            total_acknowledged=len(readers),
            readers=readers,
        )

    # ================= Inspeksi Keselamatan Kendaraan =================
    async def create_vehicle_inspection(
        self,
        data: VehicleInspectionCreate,
        current_user: CurrentUser,
    ) -> VehicleInspectionResponse:
        inspector_id = data.inspector_id or (
            UUID(str(current_user.employee_id)) if current_user.employee_id else None
        )
        if not inspector_id:
            raise AppError(
                "MISSING_INSPECTOR",
                "Akun pengguna ini tidak terhubung dengan ID Karyawan (Inspector).",
                status=400,
            )

        created = await self.inspection_repo.create(data, inspector_id)
        full_data = await self.inspection_repo.get_by_id(UUID(str(created["inspection_id"])))
        if not full_data:
            raise AppError("CREATION_FAILED", "Gagal memuat data inspeksi setelah disimpan.", status=500)
        return VehicleInspectionResponse.model_validate(full_data)

    async def list_vehicle_inspections(
        self,
        vehicle_id: UUID | None = None,
        period_type: str | None = None,
        status: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VehicleInspectionResponse]:
        items = await self.inspection_repo.list_inspections(
            vehicle_id=vehicle_id,
            period_type=period_type,
            status=status,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset,
        )
        return [VehicleInspectionResponse.model_validate(item) for item in items]

    async def get_vehicle_inspection(self, inspection_id: UUID) -> VehicleInspectionResponse:
        item = await self.inspection_repo.get_by_id(inspection_id)
        if not item:
            raise AppError("NOT_FOUND", "Data inspeksi kendaraan tidak ditemukan.", status=404)
        return VehicleInspectionResponse.model_validate(item)

    async def verify_vehicle_inspection(
        self,
        inspection_id: UUID,
        data: VehicleInspectionVerify,
        current_user: CurrentUser,
    ) -> VehicleInspectionResponse:
        verifier_uuid = UUID(str(current_user.user_id))
        updated = await self.inspection_repo.verify(inspection_id, data, verifier_uuid)
        if not updated:
            raise AppError("NOT_FOUND", "Data inspeksi tidak ditemukan untuk diverifikasi.", status=404)
        return VehicleInspectionResponse.model_validate(updated)
