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

from app.core.errors import AppError, ValidationError
from app.core.security import CurrentUser
from app.core.time import jakarta_now
from app.modules.hse.repositories.hse_campaign_repository import HseCampaignRepository
from app.modules.hse.repositories.vehicle_inspection_repository import VehicleInspectionRepository
from app.modules.hse.schemas.hse_schema import (
    HSE_CAROUSEL_MAX_SECONDS,
    HSE_CAROUSEL_MIN_SECONDS,
    HSE_MEDIA_MAX_BYTES,
    HSE_MEDIA_MIMES,
    HSE_SECONDS_PER_MEDIA,
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
        await self._validate_media(data.media_paths, data.cooldown_seconds, current_user, existing_ids=set())
        if data.media_paths:
            # Kolom media_path lama tetap terisi (foto pertama) agar klien lama masih menampilkan gambar.
            data = data.model_copy(update={"media_path": str(data.media_paths[0])})

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
        current_user: CurrentUser,
    ) -> HseCampaignResponse:
        existing = await self.campaign_repo.get_by_id(campaign_id)
        if not existing:
            raise AppError("NOT_FOUND", "Kampanye K3 tidak ditemukan.", status=404)

        if data.start_date and data.end_date and data.end_date < data.start_date:
            raise AppError("INVALID_DATE_RANGE", "Tanggal akhir tidak boleh sebelum tanggal awal.", status=400)

        if data.media_paths is not None or data.cooldown_seconds is not None:
            media = data.media_paths if data.media_paths is not None else list(existing.get("media_paths") or [])
            cooldown = data.cooldown_seconds if data.cooldown_seconds is not None else existing["cooldown_seconds"]
            kept = {str(u) for u in existing.get("media_paths") or []}
            await self._validate_media(media, cooldown, current_user, existing_ids=kept)
        if data.media_paths:
            data = data.model_copy(update={"media_path": str(data.media_paths[0])})

        updated = await self.campaign_repo.update(campaign_id, data)
        if not updated:
            raise AppError("UPDATE_FAILED", "Gagal memperbarui kampanye K3.", status=500)
        return HseCampaignResponse.model_validate(updated)

    async def delete_campaign(self, campaign_id: UUID) -> bool:
        existing = await self.campaign_repo.get_by_id(campaign_id)
        if not existing:
            raise AppError("NOT_FOUND", "Kampanye K3 tidak ditemukan.", status=404)
        return await self.campaign_repo.delete(campaign_id)

    async def _validate_media(
        self,
        media_ids: list[UUID],
        cooldown_seconds: int,
        current_user: CurrentUser,
        existing_ids: set[str],
    ) -> None:
        """Aturan carousel: foto JPG/PNG/WebP ≤ 10 MB milik pengunggah, durasi baca 10–300 dtk, min 3 dtk per foto.

        Foto yang sudah terpasang pada kampanye (existing_ids) tidak diperiksa pengunggahnya ulang.
        Kampanye tanpa foto tetap memakai aturan cooldown lama (0–300 dtk).
        """
        if not media_ids:
            return
        if len(set(media_ids)) != len(media_ids):
            raise ValidationError("Foto K3 tidak boleh sama dipilih dua kali.")
        files = await self.campaign_repo.get_media_files(media_ids)
        for file_id in media_ids:
            meta = files.get(str(file_id))
            if meta is None:
                raise ValidationError("Berkas foto K3 tidak ditemukan. Unggah ulang foto.")
            if meta["mime_type"] not in HSE_MEDIA_MIMES:
                raise ValidationError("Foto K3 harus berformat JPG, PNG, atau WebP.")
            if int(meta["byte_size"] or 0) > HSE_MEDIA_MAX_BYTES:
                raise ValidationError("Ukuran foto K3 melebihi 10 MB.")
            if str(file_id) not in existing_ids and str(meta["uploaded_by"]) != str(current_user.user_id):
                raise ValidationError("Foto K3 harus diunggah oleh Anda sendiri.")
        if not HSE_CAROUSEL_MIN_SECONDS <= cooldown_seconds <= HSE_CAROUSEL_MAX_SECONDS:
            raise ValidationError("Durasi baca kampanye bergambar harus 10 sampai 300 detik.")
        if cooldown_seconds < HSE_SECONDS_PER_MEDIA * len(media_ids):
            raise ValidationError(
                f"Durasi baca minimal {HSE_SECONDS_PER_MEDIA} detik per foto "
                f"({len(media_ids)} foto, minimal {HSE_SECONDS_PER_MEDIA * len(media_ids)} detik)."
            )

    # ================= Gerbang Popup Wajib Baca (Gate) =================
    async def get_active_popup(self, current_user: CurrentUser) -> dict[str, Any] | None:
        """
        Mengambil popup kampanye K3 wajib yang belum disetujui (unacknowledged) untuk pengguna saat ini.
        Jika tidak ada, mengembalikan None.
        """
        user_uuid = UUID(str(current_user.user_id))
        system_role = str(current_user.role)
        return await self.campaign_repo.get_active_popup_for_user(user_uuid, system_role, jakarta_now().date())

    async def mark_popup_seen(self, campaign_id: UUID, current_user: CurrentUser) -> None:
        """Dipanggil klien saat popup benar-benar tampil. Satu catatan per pengguna, kampanye, dan hari (WIB)."""
        campaign = await self.campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise AppError("NOT_FOUND", "Kampanye K3 tidak ditemukan.", status=404)
        await self.campaign_repo.mark_seen(campaign_id, UUID(str(current_user.user_id)), jakarta_now().date())

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
