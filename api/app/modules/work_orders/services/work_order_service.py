"""
app/modules/work_orders/services/work_order_service.py

Layanan logika bisnis untuk Work Orders VMS V2:
Mengatur State Machine 8 status, survei per titik, otomatisasi BoM & Item tugas,
serta penandatanganan BAST ber-fingerprint digital.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Any
from uuid import UUID

import filetype
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.security import CurrentUser
from app.core.time import utcnow
from app.modules.exports.services.builders.docx_builders import (
    bast_docx,
    order_sheet_docx,
    survey_report_docx,
)
from app.modules.exports.services.builders.model import CompletionReport
from app.modules.exports.services.builders.office_builders import completion_pptx, completion_xlsx
from app.modules.exports.services.builders.pdf_builders import completion_pdf
from app.modules.work_orders.repositories.work_order_repository import WorkOrderRepository
from app.modules.work_orders.schemas.work_order_schema import (
    SurveySubmitIn,
    WorkOrderAssignSurvey,
    WorkOrderCreate,
    WorkOrderSignBast,
)
from app.shared.access.scope_rules import sees_all_work_orders, viewer_params
from app.shared.documents.branding import default_kop_logos
from app.shared.documents.build_limiter import build_limited

SIGNATURE_MAX_BYTES = 300_000


def _decode_png(data_url: str) -> bytes:
    raw = data_url.split(",", 1)[1] if data_url.startswith("data:") else data_url
    try:
        png = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise ValidationError("Tanda tangan tidak terbaca. Ulangi tanda tangan.") from None
    if not png or len(png) > SIGNATURE_MAX_BYTES:
        raise ValidationError("Tanda tangan kosong atau terlalu besar (maks. 300 KB).")
    kind = filetype.guess(png)
    if kind is None or kind.mime != "image/png":
        raise ValidationError("Tanda tangan harus berupa gambar PNG.")
    return png


class WorkOrderService:
    """Service use case untuk Work Orders."""

    def __init__(self, db: AsyncSession, repo: WorkOrderRepository | None = None) -> None:
        self.db = db
        self.repo = repo or WorkOrderRepository(db)

    async def list_work_orders(
        self,
        current_user: CurrentUser,
        *,
        division_id: UUID | None = None,
        status: str | None = None,
        client_id: UUID | None = None,
        pm_id: UUID | None = None,
        lead_team_id: UUID | None = None,
        q: str | None = None,
        limit: int = 50,
    ) -> Sequence[Any]:
        # Cakupan: SA/OM semua; PM divisinya; ketua/anggota tim yang ditugaskan; lainnya daftar kosong.
        return await self.repo.list_work_orders(
            division_id=division_id,
            status=status,
            client_id=client_id,
            pm_id=pm_id,
            lead_team_id=lead_team_id,
            q=q,
            limit=limit,
            viewer=None if sees_all_work_orders(current_user) else viewer_params(current_user),
        )

    async def get_work_order(self, work_order_id: UUID | str, current_user: CurrentUser | None = None) -> Any:
        # Di luar cakupan → 404. `current_user` None = pemanggil internal yang sudah berwenang.
        viewer = None if current_user is None or sees_all_work_orders(current_user) else viewer_params(current_user)
        wo = await self.repo.get_work_order(work_order_id, viewer=viewer)
        if not wo:
            raise NotFoundError("Work Order tidak ditemukan.")

        points = await self.repo.list_survey_points(work_order_id)
        items = await self.repo.list_items(work_order_id)
        bom = await self.repo.list_bom(work_order_id)

        data = dict(wo._mapping) if hasattr(wo, "_mapping") else dict(wo)
        data["survey_points"] = [dict(p._mapping) if hasattr(p, "_mapping") else dict(p) for p in points]
        data["items"] = [dict(i._mapping) if hasattr(i, "_mapping") else dict(i) for i in items]
        data["bom"] = [dict(b._mapping) if hasattr(b, "_mapping") else dict(b) for b in bom]
        return data

    async def _authorize(self, user: CurrentUser, work_order_id: UUID | str, need: str, message: str) -> Any:
        """Cakupan dulu: WO di luar cakupan pengguna → 404 (keberadaannya tidak dibocorkan). Lalu hak aksi → 403:
        - `manage`: SA/OM, atau PM yang mengelola WO itu / memimpin divisinya;
        - `team`: ketua atau anggota aktif tim yang ditugaskan ke WO (kirim survei);
        - `correct`: koreksi progres item & realisasi BoM: `team` atau `manage`;
        - `signer`: ketua tim WO itu (BAST langkah 1) atau `manage` (BAST langkah 2).
        Mengembalikan baris hak akses (`on_team`, `on_leader`, `manages`)."""
        access = await self.repo.work_order_access(work_order_id, viewer_params(user))
        manages = sees_all_work_orders(user) or bool(access is not None and access.manages)
        if access is None or not (manages or access.on_team):
            raise NotFoundError("Work Order tidak ditemukan.")
        allowed = {
            "manage": manages,
            "team": bool(access.on_team),
            "correct": manages or bool(access.on_team),
            "signer": manages or bool(access.on_leader),
        }[need]
        if not allowed:
            raise ForbiddenError(message)
        return access

    async def create_work_order(self, data: WorkOrderCreate, current_user: CurrentUser) -> Any:
        # Cek kewenangan
        if not current_user.has_role("SUPER_ADMIN", "PROJECT_MANAGER", "OPERATIONAL_MANAGER"):
            raise ForbiddenError("Hanya PM, OM, atau Super Admin yang dapat membuat Work Order.")

        wo_number = await self.repo.generate_wo_number()
        payload = {
            "wo_number": wo_number,
            "client_id": str(data.client_id),
            "client_site_id": str(data.client_site_id) if data.client_site_id else None,
            "division_id": str(data.division_id),
            "pm_id": str(data.pm_id),
            "lead_team_id": str(data.lead_team_id) if data.lead_team_id else None,
            "title": data.title.strip(),
            "initial_complaint": data.initial_complaint.strip() if data.initial_complaint else None,
        }
        new_id = await self.repo.create_work_order(payload)
        return await self.get_work_order(new_id)

    async def assign_survey(
        self, work_order_id: UUID | str, data: WorkOrderAssignSurvey, current_user: CurrentUser
    ) -> Any:
        if not current_user.has_role("SUPER_ADMIN", "PROJECT_MANAGER", "OPERATIONAL_MANAGER"):
            raise ForbiddenError("Hanya PM, OM, atau Super Admin yang dapat menugaskan survei.")
        await self._authorize(current_user, work_order_id, "manage",
                              "Hanya PM WO ini atau PM/OM divisinya yang dapat menugaskan survei.")
        wo = await self.repo.get_work_order(work_order_id)
        if not wo:
            raise NotFoundError("Work Order tidak ditemukan.")
        if wo.status not in ("WAITING_SURVEY", "SURVEY_IN_PROGRESS"):
            raise AppError("INVALID_STATE", f"Penugasan survei tidak valid untuk status {wo.status}.", status=409)

        await self.repo.assign_survey(
            work_order_id=work_order_id,
            lead_team_id=data.lead_team_id,
            survey_date=data.survey_date,
            notes=data.notes,
        )
        return await self.get_work_order(work_order_id)

    async def submit_survey(
        self, work_order_id: UUID | str, data: SurveySubmitIn, current_user: CurrentUser
    ) -> Any:
        await self._authorize(current_user, work_order_id, "team",
                              "Hanya anggota tim yang ditugaskan ke WO ini yang dapat mengirim laporan survei.")
        wo = await self.repo.get_work_order(work_order_id)
        if not wo:
            raise NotFoundError("Work Order tidak ditemukan.")
        if wo.status not in ("WAITING_SURVEY", "SURVEY_IN_PROGRESS", "SURVEY_SUBMITTED"):
            raise AppError("INVALID_STATE", f"Laporan survei tidak dapat dikirim untuk status {wo.status}.", status=409)

        points_payload = [p.model_dump() for p in data.points]
        if not await self.repo.submit_survey(
            work_order_id=work_order_id,
            surveyor_team_id=wo.lead_team_id,
            narrative=data.narrative,
            format_type=data.format,
            points=points_payload,
            general_bom=data.general_bom,
        ):
            raise AppError("INVALID_STATE", "Status WO berubah; laporan survei tidak dapat dikirim. Muat ulang.",
                           status=409)
        return await self.get_work_order(work_order_id)

    async def apply_survey(self, work_order_id: UUID | str, current_user: CurrentUser) -> Any:
        """
        Fitur Inti: PM menyetujui survei dan mengunci item tugas & BOM.
        """
        if not current_user.has_role("SUPER_ADMIN", "PROJECT_MANAGER", "OPERATIONAL_MANAGER"):
            raise ForbiddenError("Hanya PM atau OM yang dapat menyetujui survei dan mengunci daftar tugas.")
        await self._authorize(current_user, work_order_id, "manage",
                              "Hanya PM WO ini atau PM/OM divisinya yang dapat menyetujui survei.")

        wo = await self.repo.get_work_order(work_order_id)
        if not wo:
            raise NotFoundError("Work Order tidak ditemukan.")
        if wo.status != "SURVEY_SUBMITTED":
            raise AppError(
                "INVALID_STATE",
                f"Survei hanya dapat disetujui jika berstatus SURVEY_SUBMITTED (saat ini: {wo.status}).",
                status=409,
            )

        if not await self.repo.apply_survey_to_items(work_order_id, current_user.user_id):
            raise AppError(
                "INVALID_STATE",
                "Survei sudah disetujui atau status WO berubah; muat ulang.",
                status=409,
            )
        return await self.get_work_order(work_order_id)

    async def update_item_progress(
        self,
        item_id: UUID | str,
        completed_qty: Decimal,
        status: str,
        photo_slots_snapshot: list[dict[str, Any]] | None,
        current_user: CurrentUser,
    ) -> None:
        work_order_id = await self.repo.work_order_of_item(item_id)
        if work_order_id is None:
            raise NotFoundError("Item pekerjaan tidak ditemukan.")
        await self._authorize(current_user, work_order_id, "correct",
                              "Hanya anggota/ketua tim yang ditugaskan ke WO ini atau PM/OM dalam cakupan yang dapat "
                              "mengubah progres.")
        await self.repo.update_item_progress(
            item_id=item_id,
            completed_qty=completed_qty,
            status=status,
            photo_slots_snapshot=photo_slots_snapshot,
        )

    async def update_bom_actual(self, bom_id: UUID | str, actual_qty: Decimal, current_user: CurrentUser) -> None:
        work_order_id = await self.repo.work_order_of_bom(bom_id)
        if work_order_id is None:
            raise NotFoundError("Item BoM tidak ditemukan.")
        await self._authorize(current_user, work_order_id, "correct",
                              "Hanya anggota/ketua tim yang ditugaskan ke WO ini atau PM/OM dalam cakupan yang dapat "
                              "mencatat realisasi BoM.")
        await self.repo.update_bom_actual(bom_id=bom_id, actual_qty=actual_qty)

    async def sign_bast(
        self, work_order_id: UUID | str, data: WorkOrderSignBast, current_user: CurrentUser
    ) -> Any:
        """BAST berurutan: (1) ketua tim WO menandatangani → status COMPLETED; (2) PM/OM dalam cakupan
        menandatangani sebagai persetujuan final → BAST_SIGNED (status 'selesai'). Pemanggil yang sama tidak boleh
        menandatangani kedua langkah."""
        access = await self._authorize(current_user, work_order_id, "signer",
                                       "Hanya ketua tim yang ditugaskan ke WO ini atau PM/OM divisinya yang dapat "
                                       "menandatangani BAST.")
        wo = await self.repo.get_work_order(work_order_id)
        if not wo:
            raise NotFoundError("Work Order tidak ditemukan.")
        is_manager = sees_all_work_orders(current_user) or bool(access.manages)

        if access.on_leader and not wo.leader_signed_at:
            await self._sign_bast_leader(work_order_id, wo, data, current_user)
        elif not is_manager:
            raise AppError("BAST_ALREADY_SIGNED",
                           "Ketua tim sudah menandatangani BAST. Menunggu persetujuan final PM/OM divisi.",
                           status=409)
        else:
            await self._sign_bast_final(work_order_id, wo, data, current_user)
        return await self.get_work_order(work_order_id)

    async def _ensure_items_done(self, work_order_id: UUID | str) -> None:
        items = await self.repo.list_items(work_order_id)
        if not items:
            raise ValidationError("Work order belum memiliki daftar tugas pekerjaan.")
        unfinished = [i for i in items if i.status != "DONE"]
        if unfinished:
            raise ValidationError(
                f"Terdapat {len(unfinished)} item pekerjaan yang belum selesai (DONE). "
                "Selesaikan seluruh item sebelum menandatangani BAST."
            )

    async def _store_signature(self, wo: Any, work_order_id: UUID | str, png: bytes, current_user: CurrentUser) -> str:
        sig_id = str(uuid.uuid4())
        storage_key = f"{wo.division_id}/bast_{work_order_id}_{sig_id[:8]}.png"
        storage.upload_file(storage_key, png, "image/png")
        target_office_id: str | UUID = (
            getattr(wo, "pm_office_id", None)
            or getattr(current_user, "organization_id", None)
            or str(wo.division_id)
        )
        return await self.repo.insert_signature_file(
            file_id=sig_id,
            org_id=target_office_id,
            storage_key=storage_key,
            file_name=f"bast_signature_{wo.wo_number}.png",
            mime_type="image/png",
            byte_size=len(png),
            sha256=hashlib.sha256(png).digest(),
            user_id=current_user.user_id,
        )

    async def _sign_bast_leader(
        self, work_order_id: UUID | str, wo: Any, data: WorkOrderSignBast, current_user: CurrentUser
    ) -> None:
        """Langkah 1: tanda tangan ketua tim. Semua item harus DONE; status menjadi COMPLETED."""
        if wo.status not in ("READY_TO_EXECUTE", "IN_PROGRESS", "COMPLETED"):
            raise AppError("INVALID_STATE", f"BAST tidak dapat ditandatangani untuk status {wo.status}.", status=409)
        await self._ensure_items_done(work_order_id)
        signature_file_id = None
        if data.signature_data_uri:
            signature_file_id = await self._store_signature(
                wo, work_order_id, _decode_png(data.signature_data_uri), current_user)
        ok = await self.repo.sign_bast_leader(
            work_order_id=work_order_id,
            signer_user_id=current_user.user_id,
            signer_name=data.signer_name.strip(),
            signature_file_id=signature_file_id,
        )
        if not ok:
            raise AppError("INVALID_STATE", "BAST tidak dapat ditandatangani ketua tim pada kondisi saat ini.",
                           status=409)

    async def _sign_bast_final(
        self, work_order_id: UUID | str, wo: Any, data: WorkOrderSignBast, current_user: CurrentUser
    ) -> None:
        """Langkah 2: persetujuan final PM/OM. Hanya setelah ketua tim; penandatangan harus orang lain."""
        if wo.leader_signed_at is None:
            raise AppError("LEADER_SIGNATURE_REQUIRED",
                           "Ketua tim harus menandatangani berita acara lebih dulu.", status=409)
        if wo.leader_signed_by is not None and str(wo.leader_signed_by) == str(current_user.user_id):
            raise AppError("SAME_SIGNER",
                           "Persetujuan final harus dilakukan PM/OM, bukan oleh penandatangan ketua tim.", status=409)
        if wo.status != "COMPLETED":
            raise AppError("INVALID_STATE", f"Persetujuan final BAST tidak dapat dilakukan untuk status {wo.status}.",
                           status=409)
        await self._ensure_items_done(work_order_id)

        signature_file_id: str | None = None
        sig_png: bytes | None = None
        if data.signature_data_uri:
            sig_png = _decode_png(data.signature_data_uri)
            signature_file_id = await self._store_signature(wo, work_order_id, sig_png, current_user)

        # Hitung sidik verifikasi digital dokumen BAST (memuat tanda tangan ketua tim bila ada)
        bom = await self.repo.list_bom(work_order_id)
        bom_serialized = [
            (b.item_name, str(b.unit), float(b.estimated_qty), float(b.actual_qty))
            for b in bom
        ]
        fingerprint_content = {
            "work_order_id": str(work_order_id),
            "wo_number": wo.wo_number,
            "client_name": wo.client_name,
            "title": wo.title,
            "signer_name": data.signer_name.strip(),
            "signed_by_user": str(current_user.user_id),
            "bom": bom_serialized,
            "sig_hash": hashlib.sha256(sig_png or b"").hexdigest(),
        }
        if wo.leader_signed_at is not None:
            fingerprint_content["leader"] = [
                str(wo.leader_signed_by),
                wo.leader_signed_at.isoformat(),
                str(wo.leader_signature_file_id),
                wo.leader_signer_name,
            ]
        verify_hash = hashlib.sha256(
            json.dumps(fingerprint_content, sort_keys=True).encode()
        ).hexdigest()

        ok = await self.repo.sign_bast(
            work_order_id=work_order_id,
            signer_name=data.signer_name.strip(),
            signature_file_id=signature_file_id,
            verify_hash=verify_hash,
        )
        if not ok:
            raise AppError("INVALID_STATE", "BAST tidak dapat disahkan pada kondisi saat ini.", status=409)

    async def build_export(
        self, work_order_id: UUID | str, template: str, current_user: CurrentUser
    ) -> tuple[str, str, bytes]:
        """Menghasilkan dokumen resmi ekspor untuk Work Order.
        Mendukung BAST_PDF, BAST_DOCX, SURVEY_REPORT, ORDER_SHEET, BOQ, PROGRESS_SLIDES.
        """
        if not current_user.has_role("SUPER_ADMIN", "PROJECT_MANAGER", "OPERATIONAL_MANAGER"):
            raise ForbiddenError("Hanya PM, OM, atau Super Admin yang dapat mengunduh dokumen resmi.")
        await self._authorize(current_user, work_order_id, "manage",
                              "Hanya PM WO ini atau PM/OM divisinya yang dapat mengunduh dokumen resmi.")
        detail = await self.get_work_order(work_order_id, current_user)
        order_dict = {
            "completion_id": str(detail["work_order_id"]),
            "project_title": detail["title"],
            "client_name": detail["client_name"] or "PT Visiontech Indograha",
            "division_name": detail["division_name"] or "Operasional",
            "pm_name": detail["pm_name"] or "Project Manager",
            "site_address": detail["site_address"] or "-",
            "signature_hash": detail.get("bast_signed_at") and "VERIFIED_HASH",
            "bast_signed_at": detail.get("bast_signed_at"),
            "bast_signer_name": detail.get("bast_signer_name") or "PIC Klien",
        }
        report = CompletionReport(
            order=order_dict,
            points=[],
            roster=[],
            bom=detail.get("bom", []),
            generated_by="PM",
            generated_at=utcnow(),
            verify_url=f"/verify/work-completion/{detail['work_order_id']}",
            logos=default_kop_logos(),
        )

        template_upper = template.upper()
        wo_num = str(detail["wo_number"]).replace("/", "-")
        docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        if template_upper in ("PDF", "BAST_PDF"):
            content = await build_limited(completion_pdf, report)
            return f"BAST_{wo_num}.pdf", "application/pdf", content
        elif template_upper in ("DOCX", "BAST", "BAST_DOCX"):
            content = bast_docx(report)
            return f"BAST_{wo_num}.docx", docx_mime, content
        elif template_upper in ("SURVEY", "SURVEY_REPORT"):
            content = survey_report_docx(report)
            return f"Laporan_Survei_{wo_num}.docx", docx_mime, content
        elif template_upper in ("ORDER_SHEET", "ORDER"):
            content = order_sheet_docx(report)
            return f"Surat_Tugas_{wo_num}.docx", docx_mime, content
        elif template_upper in ("BOQ", "XLSX"):
            content = completion_xlsx(report)
            xlsx_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            return f"Rekap_Material_{wo_num}.xlsx", xlsx_mime, content
        elif template_upper in ("SLIDES", "PPTX", "PROGRESS_SLIDES"):
            content = completion_pptx(report)
            pptx_mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            return f"Slide_Progres_{wo_num}.pptx", pptx_mime, content
        else:
            raise ValidationError(f"Format ekspor tidak dikenali: {template}")
