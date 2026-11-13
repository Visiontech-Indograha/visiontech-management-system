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

from app.core import system_settings
from app.core.errors import AppError, ValidationError
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.hse.repositories.hse_campaign_repository import HseCampaignRepository
from app.modules.hse.repositories.vehicle_inspection_repository import VehicleInspectionRepository
from app.modules.hse.schemas.hse_schema import (
    HSE_CAPTION_MAX_CHARS,
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
    InspectionChecklistItem,
    InspectionChecklistTemplate,
    VehicleInspectionCreate,
    VehicleInspectionResponse,
    VehicleInspectionVerify,
)
from app.shared.access.office_scope import office_restriction, offices_param

_INSPECTION_ITEMS: tuple[tuple[str, str], ...] = (
    ("rem", "Rem"), ("ban", "Ban dan tekanan angin"), ("oli_mesin", "Oli mesin"),
    ("lampu", "Lampu depan, belakang, dan sein"), ("klakson", "Klakson"), ("spion", "Spion"),
    ("wiper", "Wiper dan air kaca"), ("sabuk_pengaman", "Sabuk pengaman"), ("apar", "Alat pemadam api (APAR)"),
    ("p3k", "Kotak P3K"), ("air_radiator", "Air radiator"), ("bbm", "Bahan bakar"),
)


class HseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.campaign_repo = HseCampaignRepository(db)
        self.inspection_repo = VehicleInspectionRepository(db)

    async def _offices(self, user: CurrentUser | None, perm: Permission) -> list[str] | None:
        """None = semua kantor. HSE yang hanya peran tambahan (ADR 0002 fase 2) dibatasi ke kantor penugasannya
        bila ROLE_ASSIGNMENT_ENABLED; HSE utama, SA, dan flag mati = perilaku lama."""
        if user is None:
            return None
        restriction = await office_restriction(self.db, user, perm)
        return None if restriction is None else offices_param(restriction) or ["00000000-0000-0000-0000-000000000000"]

    async def _ensure_campaign_scope(
        self, user: CurrentUser | None, audience: str | None, target_user_ids: list[Any] | None,
        *, existing: bool = False,
    ) -> None:
        """Penerbit K3 yang dibatasi kantor (HSE peran tambahan, ADR 0002) hanya boleh menerbitkan kampanye yang
        seluruhnya menjangkau pengguna di kantor penugasannya: audiens INDIVIDUAL dengan semua sasaran di kantor itu.
        Audiens ALL/FIELD/OFFICE menjangkau semua kantor, jadi ditolak sampai K3 punya kolom kantor (G2-K3).
        `existing`: kampanye yang sudah ada di luar cakupan dijawab 404 (keberadaannya tidak dibocorkan)."""
        offices = await self._offices(user, Permission.MANAGE_HSE_CAMPAIGNS)
        if offices is None:
            return
        ids = [str(u) for u in (target_user_ids or [])]
        ok = False
        if audience == "INDIVIDUAL" and ids:
            ok = bool(await self.campaign_repo.scalar(
                """
                SELECT COUNT(*) = CAST(:n AS int) FROM users u
                JOIN employee e ON e.employee_id = u.employee_id AND e.delete_at IS NULL
                WHERE u.user_id = ANY(CAST(:ids AS uuid[])) AND u.delete_at IS NULL
                  AND e.office_id = ANY(CAST(:offices AS uuid[]))
                """,
                {"ids": ids, "n": len(set(ids)), "offices": offices},
            )) if len(set(ids)) == len(ids) else False
        if ok:
            return
        if existing:
            raise AppError("NOT_FOUND", "Kampanye K3 tidak ditemukan.", status=404)
        raise AppError(
            "OFFICE_SCOPE_FORBIDDEN",
            "Anda hanya dapat menerbitkan K3 untuk karyawan di kantor penugasan Anda (pilih sasaran perorangan).",
            status=403,
        )

    # ================= Kampanye K3 =================
    async def create_campaign(
        self,
        data: HseCampaignCreate,
        current_user: CurrentUser,
    ) -> HseCampaignResponse:
        if data.end_date < data.start_date:
            raise AppError("INVALID_DATE_RANGE", "Tanggal akhir kampanye tidak boleh sebelum tanggal awal.", status=400)
        await self._ensure_campaign_scope(current_user, data.target_audience, data.target_user_ids)
        await self._validate_media(data.media_paths, data.cooldown_seconds, current_user, existing_ids=set())
        self._validate_captions(data.media_paths, data.media_captions)
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
        await self._ensure_campaign_scope(
            current_user, existing.get("target_audience"), existing.get("target_user_ids"), existing=True)
        if data.target_audience is not None or data.target_user_ids is not None:
            await self._ensure_campaign_scope(
                current_user,
                data.target_audience if data.target_audience is not None else existing.get("target_audience"),
                data.target_user_ids if data.target_user_ids is not None else existing.get("target_user_ids"))

        if data.start_date and data.end_date and data.end_date < data.start_date:
            raise AppError("INVALID_DATE_RANGE", "Tanggal akhir tidak boleh sebelum tanggal awal.", status=400)

        if data.media_paths is not None or data.media_captions is not None:
            effective_media = (
                data.media_paths if data.media_paths is not None else list(existing.get("media_paths") or [])
            )
            effective_captions = (
                data.media_captions if data.media_captions is not None else list(existing.get("media_captions") or [])
            )
            self._validate_captions(effective_media, effective_captions)
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

    async def delete_campaign(self, campaign_id: UUID, user: CurrentUser | None = None) -> bool:
        existing = await self.campaign_repo.get_by_id(campaign_id)
        if not existing:
            raise AppError("NOT_FOUND", "Kampanye K3 tidak ditemukan.", status=404)
        await self._ensure_campaign_scope(
            user, existing.get("target_audience"), existing.get("target_user_ids"), existing=True)
        return await self.campaign_repo.delete(campaign_id)

    @staticmethod
    def _validate_captions(media_ids: list[UUID], captions: list[str]) -> None:
        """Keterangan kosong atau sejajar dengan foto; tiap keterangan maks 300 karakter."""
        if not captions:
            return
        if len(captions) != len(media_ids):
            raise ValidationError("Jumlah keterangan harus sama dengan jumlah foto.")
        if any(len(text) > HSE_CAPTION_MAX_CHARS for text in captions):
            raise ValidationError(f"Keterangan foto maksimal {HSE_CAPTION_MAX_CHARS} karakter.")

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
        # Flag hidup: peran efektif (utama + penugasan aktif) agar peran tambahan ikut melihat kampanye K3
        # untuk perannya. Flag mati: hanya peran utama (persis lama).
        roles = list(current_user.roles) if system_settings.role_assignment_enabled() else None
        return await self.campaign_repo.get_active_popup_for_user(user_uuid, system_role, roles)

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

    async def get_campaign_audit_stats(
        self, campaign_id: UUID, user: CurrentUser | None = None,
    ) -> HseCampaignAuditStats:
        campaign = await self.campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise AppError("NOT_FOUND", "Kampanye K3 tidak ditemukan.", status=404)

        raw_readers = await self.campaign_repo.list_readers_by_campaign(
            campaign_id, await self._offices(user, Permission.VIEW_HSE_CAMPAIGNS))
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
        me = str(current_user.employee_id) if current_user.employee_id else None
        manager = Permission.MANAGE_VEHICLE_INSPECTIONS.value in current_user.permissions
        leader = current_user.has_role("TEAM_LEADER")
        inspector_id: UUID | None
        if manager:
            inspector_id = data.inspector_id or (UUID(me) if me else None)
        else:
            # Pengemudi terdaftar aktif atau ketua tim: hanya atas nama sendiri.
            inspector_id = UUID(me) if me else None
            if not me or not (leader or await self.inspection_repo.has_active_driver_row(me)):
                raise AppError("FORBIDDEN", "Anda tidak berhak mengirim inspeksi kendaraan.", status=403)
        if not inspector_id:
            raise AppError(
                "MISSING_INSPECTOR",
                "Akun pengguna ini tidak terhubung dengan ID Karyawan (Inspector).",
                status=400,
            )

        exists, office = await self.inspection_repo.vehicle_office(data.vehicle_id)
        if manager:
            offices = await self._offices(current_user, Permission.MANAGE_VEHICLE_INSPECTIONS)
            allowed = exists and (offices is None or office in offices)
        else:
            assert me is not None
            allowed = exists and (
                await self.inspection_repo.is_active_driver(data.vehicle_id, me)
                or (leader and office is not None and office == await self.inspection_repo.employee_office(me))
            )
        if not allowed:
            raise AppError("NOT_FOUND", "Kendaraan tidak ditemukan.", status=404)
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
        user: CurrentUser | None = None,
        q: str | None = None,
        mine: str | None = None,
    ) -> tuple[list[VehicleInspectionResponse], int]:
        items, total = await self.inspection_repo.list_inspections(
            vehicle_id=vehicle_id,
            period_type=period_type,
            status=status,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset,
            offices=None if mine else await self._offices(user, Permission.VIEW_VEHICLE_INSPECTIONS),
            q=q,
            mine=mine,
        )
        return [VehicleInspectionResponse.model_validate(item) for item in items], total

    def inspection_checklist_template(self) -> InspectionChecklistTemplate:
        """Butir daftar periksa baku untuk layar Buat inspeksi (web dan HP memakai daftar yang sama)."""
        ok = ["BAIK", "PERLU_PERBAIKAN", "RUSAK"]
        return InspectionChecklistTemplate(
            period_types=["DAILY", "WEEKLY", "MONTHLY"],
            items=[InspectionChecklistItem(key=k, label=label, options=ok) for k, label in _INSPECTION_ITEMS],
        )

    async def _inspection_visible(self, item: dict[str, Any] | None, user: CurrentUser | None,
                                  perm: Permission) -> bool:
        if not item:
            return False
        offices = await self._offices(user, perm)
        return offices is None or str(item.get("office_id")) in offices

    async def get_vehicle_inspection(
        self, inspection_id: UUID, user: CurrentUser | None = None,
    ) -> VehicleInspectionResponse:
        item = await self.inspection_repo.get_by_id(inspection_id)
        if not await self._inspection_visible(item, user, Permission.VIEW_VEHICLE_INSPECTIONS) or item is None:
            raise AppError("NOT_FOUND", "Data inspeksi kendaraan tidak ditemukan.", status=404)
        return VehicleInspectionResponse.model_validate(item)

    async def verify_vehicle_inspection(
        self,
        inspection_id: UUID,
        data: VehicleInspectionVerify,
        current_user: CurrentUser,
    ) -> VehicleInspectionResponse:
        existing = await self.inspection_repo.get_by_id(inspection_id)
        if not await self._inspection_visible(existing, current_user, Permission.MANAGE_VEHICLE_INSPECTIONS):
            raise AppError("NOT_FOUND", "Data inspeksi tidak ditemukan untuk diverifikasi.", status=404)
        verifier_uuid = UUID(str(current_user.user_id))
        updated = await self.inspection_repo.verify(inspection_id, data, verifier_uuid)
        if not updated:
            raise AppError("NOT_FOUND", "Data inspeksi tidak ditemukan untuk diverifikasi.", status=404)
        return VehicleInspectionResponse.model_validate(updated)
