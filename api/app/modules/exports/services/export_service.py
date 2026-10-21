"""
app/modules/exports/services/export_service.py
Ekspor dokumen resmi (Milestone 8, docs/35 §8): rakit data → builder → simpan ke storage → catat di
`document_template_export` → unduh ulang dari registri.

Akses:
- Dokumen order: siapa pun yang boleh melihat order (WorkCompletionService). PDF resmi hanya setelah disahkan PM.
- Rekap periodik divisi: PM/OM divisi itu atau SUPER_ADMIN; unduh ulang oleh pembuatnya, OM, atau SUPER_ADMIN.
Berkas yang tak boleh dilihat → 404.
"""
from __future__ import annotations

import io
import re
from collections.abc import Callable
from datetime import date
from typing import Any
from uuid import UUID

from PIL import Image, UnidentifiedImageError

from app.core import storage
from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.security import CurrentUser
from app.core.time import jakarta_now
from app.modules.exports.repositories.export_repository import ExportRepository, photo_refs
from app.modules.exports.services.builders.docx_builders import bast_docx, survey_report_docx
from app.modules.exports.services.builders.model import CompletionReport, PeriodicReport, ReportPhoto, ReportPoint
from app.modules.exports.services.builders.office_builders import (
    completion_pptx,
    completion_xlsx,
    periodic_pptx,
    periodic_xlsx,
)
from app.modules.exports.services.builders.pdf_builders import completion_pdf
from app.modules.work_completion.services.work_completion_service import WorkCompletionService, verify_url
from app.shared.access.access_service import check_division_manager, is_admin

MIME = {
    "WORD_DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "PDF": "application/pdf",
    "EXCEL_XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "PPTX": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
EXT = {"WORD_DOCX": "docx", "PDF": "pdf", "EXCEL_XLSX": "xlsx", "PPTX": "pptx"}
# template → (format, builder, berkas templat baku yang dipakai)
COMPLETION_TEMPLATES: dict[str, tuple[str, Callable[[CompletionReport], bytes], str]] = {
    "BAST": ("WORD_DOCX", bast_docx, "builtin:bast-docx-v2"),
    "SURVEY_REPORT": ("WORD_DOCX", survey_report_docx, "builtin:survey-report-docx-v1"),
    "BAST_PDF": ("PDF", completion_pdf, "templates/completion_report.html"),
    "BOQ": ("EXCEL_XLSX", completion_xlsx, "builtin:boq-xlsx-v1"),
    "PROGRESS_SLIDES": ("PPTX", completion_pptx, "builtin:progress-pptx-v1"),
}
PERIODIC = {
    "EXCEL_XLSX": ("PERIODIC_RECAP", periodic_xlsx, "builtin:periodic-xlsx-v1"),
    "PPTX": ("PERIODIC_SLIDES", periodic_pptx, "builtin:periodic-pptx-v1"),
}
MAX_PERIOD_DAYS = 31
MAX_PHOTOS_PER_POINT = 6
MAX_PHOTOS = 40
PHOTO_EDGE = 1280
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _shrink(image: bytes) -> bytes | None:
    """Perkecil foto (sisi terpanjang 1280 px, JPEG) agar dokumen tetap ringan; bukan gambar → None."""
    try:
        with Image.open(io.BytesIO(image)) as source:
            img = source.convert("RGB")
            img.thumbnail((PHOTO_EDGE, PHOTO_EDGE))
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=82)
            return buf.getvalue()
    except (UnidentifiedImageError, OSError, ValueError):
        return None


def _slug(text: str | None) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text or "").strip("-")[:40] or "dokumen"


def file_name(record: Any) -> str:
    stamp = record.create_at.strftime("%Y%m%d-%H%M")
    return f"{record.template_type}_{stamp}.{EXT.get(record.export_format, 'bin')}"


class ExportService:
    def __init__(self, repo: ExportRepository, orders: WorkCompletionService) -> None:
        self.repo = repo
        self.orders = orders

    # ── Dokumen order ─────────────────────────────────────────────────────────
    async def export_completion(self, user: CurrentUser, completion_id: UUID, template: str) -> tuple[Any, bytes]:
        order = await self.orders.get_order_detail(user, completion_id)
        export_format, build, master = COMPLETION_TEMPLATES[template]
        if template == "BAST_PDF" and not order.get("signature_hash"):
            raise AppError("NOT_SIGNED", "PDF resmi tersedia setelah berita acara disahkan PM.", status=409)
        report = await self._completion_report(order, user)
        if template == "SURVEY_REPORT" and not report.survey_points:
            raise AppError("NO_SURVEY_ITEMS", "Order ini belum punya item fase Survei.", status=422)
        content = build(report)
        key = (f"exports/work-completion/{completion_id}/{jakarta_now():%Y%m%d-%H%M%S}_"
               f"{template.lower()}_{_slug(order.get('client_name'))}.{EXT[export_format]}")
        record = await self._store(user, key, content, export_format, source_type="WORK_COMPLETION",
                                   completion_id=completion_id, template_type=template, master=master)
        return record, content

    async def list_for_completion(self, user: CurrentUser, completion_id: UUID) -> list[Any]:
        await self.orders.get_order_detail(user, completion_id)
        return await self.repo.list_exports(completion_id=completion_id)

    # ── Rekap periodik divisi ────────────────────────────────────────────────
    async def export_periodic(self, user: CurrentUser, division_id: UUID, start: date, end: date,
                              export_format: str) -> tuple[Any, bytes]:
        if end < start:
            raise ValidationError("Tanggal akhir harus sama atau setelah tanggal awal.")
        if (end - start).days >= MAX_PERIOD_DAYS:
            raise ValidationError(f"Rentang rekap paling lama {MAX_PERIOD_DAYS} hari.")
        await check_division_manager(self.repo.db, division_id, user)
        template_type, build, master = PERIODIC[export_format]
        report = PeriodicReport(
            division_name=await self.repo.division_name(division_id) or "-", start=start, end=end,
            days=await self.repo.periodic_days(division_id, start, end),
            boq=await self.repo.periodic_boq(division_id, start, end),
            meal=await self.repo.periodic_meal(division_id, start, end),
            generated_by=user.email, generated_at=jakarta_now(),
        )
        content = build(report)
        key = (f"exports/periodic/{division_id}/{start:%Y%m%d}-{end:%Y%m%d}_{jakarta_now():%H%M%S}_"
               f"{template_type.lower()}.{EXT[export_format]}")
        record = await self._store(user, key, content, export_format, source_type="WORK_PLAN_PERIODIC",
                                   template_type=template_type, master=master, period=(start, end))
        return record, content

    async def list_periodic(self, user: CurrentUser) -> list[Any]:
        sees_all = is_admin(user) or user.role == "OPERATIONAL_MANAGER"
        if not sees_all and not user.employee_id:
            return []
        return await self.repo.list_exports(generated_by=None if sees_all else user.employee_id)

    # ── Unduh ulang dari registri ────────────────────────────────────────────
    async def download(self, user: CurrentUser, export_id: UUID) -> tuple[Any, bytes]:
        record = await self.repo.get_export(export_id)
        if record is None:
            raise NotFoundError("Dokumen")
        if record.completion_id is not None:
            await self.orders.get_order_detail(user, record.completion_id)  # tak terlihat → 404
        elif not (is_admin(user) or user.role == "OPERATIONAL_MANAGER"
                  or str(record.generated_by_id) == str(user.employee_id)):
            raise NotFoundError("Dokumen")
        content = storage.get_object_bytes(record.file_output_url)
        if content is None:
            raise AppError("FILE_GONE", "Berkas dokumen tidak ditemukan di penyimpanan. Buat ulang dokumennya.",
                           status=404)
        return record, content

    # ── Internal ─────────────────────────────────────────────────────────────
    async def _store(self, user: CurrentUser, key: str, content: bytes, export_format: str, *, source_type: str,
                     template_type: str, master: str, completion_id: UUID | None = None,
                     period: tuple[date, date] | None = None) -> Any:
        if not user.employee_id:
            raise ForbiddenError("Akun ini belum tertaut ke data karyawan.")
        if not storage.upload_file(key, content, MIME[export_format]):
            raise AppError("STORAGE_UNAVAILABLE", "Penyimpanan berkas sedang tidak tersedia. Coba lagi.", status=503)
        return await self.repo.insert_export(
            source_type=source_type, completion_id=completion_id, period_start=period[0] if period else None,
            period_end=period[1] if period else None, template_type=template_type, master_template=master,
            export_format=export_format, storage_key=key, generated_by=user.employee_id,
        )

    async def _completion_report(self, order: dict[str, Any], user: CurrentUser) -> CompletionReport:
        items = await self.repo.completion_items(order["completion_id"])
        item_refs = {str(i.item_id): photo_refs(i.photos)[:MAX_PHOTOS_PER_POINT] for i in items}
        order_refs = photo_refs(order.get("realization_photos_json"))[:MAX_PHOTOS_PER_POINT * 2]
        all_refs = [r for refs in item_refs.values() for r in refs] + order_refs
        file_ids = list(dict.fromkeys(r["file_id"] for r in all_refs if r["file_id"] and _UUID.match(r["file_id"])))
        keys = await self.repo.image_keys(file_ids[:MAX_PHOTOS])
        names = await self.repo.requirement_names(
            list({str(r["requirement_id"]) for r in all_refs if r.get("requirement_id")}))
        images: dict[str, bytes] = {}
        for fid, key in keys.items():
            raw = storage.get_object_bytes(key)
            small = _shrink(raw) if raw else None
            if small:
                images[fid] = small

        def photos(refs: list[dict[str, str | None]], fallback: str) -> list[ReportPhoto]:
            return [ReportPhoto(names.get(str(r.get("requirement_id")), fallback), images[str(r["file_id"])])
                    for r in refs if str(r["file_id"]) in images]

        bom = list(order.get("bom_items") or [])
        points = [
            ReportPoint(
                item_id=str(i.item_id), title=i.title, phase=i.task_phase, status=i.status, work_date=i.work_date,
                team_name=i.team_name, location=i.location_name or i.site_name or "", lat=i.site_lat, lng=i.site_lng,
                target=i.target_qty, completed=i.completed_qty, progress=i.progress_percent, notes=i.notes,
                delay_reason=i.delay_reason, assignees=i.assignees, work_type=i.work_type_name,
                photos=photos(item_refs[str(i.item_id)], "Foto titik"),
                bom=[b for b in bom if str(b.get("work_plan_item_id")) == str(i.item_id)],
            )
            for i in items
        ]
        roster = await self.repo.team_roster(list(dict.fromkeys(str(i.team_id) for i in items)))
        leader_key, pm_key = order.get("leader_signature_path"), order.get("pm_signature_path")
        return CompletionReport(
            order=order, points=points, roster=roster, bom=bom, generated_by=user.email,
            generated_at=jakarta_now(), verify_url=verify_url(order), photos=photos(order_refs, "Foto realisasi"),
            leader_signature=storage.get_object_bytes(leader_key) if leader_key else None,
            pm_signature=storage.get_object_bytes(pm_key) if pm_key else None,
        )
