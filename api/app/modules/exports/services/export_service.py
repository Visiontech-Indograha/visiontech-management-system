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

import asyncio
import io
import re
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from PIL import Image, UnidentifiedImageError

from app.core import storage
from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.security import CurrentUser
from app.core.time import jakarta_now
from app.modules.exports.repositories.export_repository import ExportRepository, photo_refs
from app.modules.exports.services.builders.docx_builders import (
    bast_docx,
    daily_report_docx,
    order_sheet_docx,
    survey_report_docx,
)
from app.modules.exports.services.builders.model import (
    AssetLine,
    CompletionReport,
    DailyReport,
    PeriodicReport,
    ReportPhoto,
    ReportPoint,
    TeamWeekReport,
    tgl,
)
from app.modules.exports.services.builders.office_builders import (
    completion_pptx,
    completion_xlsx,
    periodic_pptx,
    periodic_xlsx,
    team_week_pptx,
)
from app.modules.exports.services.builders.pdf_builders import completion_pdf
from app.modules.exports.services.builders.survey_template import (
    FO_COLUMNS,
    SurveyDoc,
    SurveyPhoto,
    SurveyPointDoc,
    build_survey_docx,
)
from app.modules.work_completion.services.work_completion_service import WorkCompletionService, verify_url
from app.modules.work_plans.services.survey_service import SurveyService
from app.shared.access.access_service import DailyNeed, check_daily_access, check_division_manager, is_admin
from app.shared.documents import branding
from app.shared.documents.office_convert import docx_to_pdf
from app.shared.documents.static_map import MapPoint, render_point_map

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
    "ORDER_SHEET": ("WORD_DOCX", order_sheet_docx, "builtin:order-sheet-docx-v1"),
    "BOQ": ("EXCEL_XLSX", completion_xlsx, "builtin:boq-xlsx-v1"),
    "PROGRESS_SLIDES": ("PPTX", completion_pptx, "builtin:progress-pptx-v1"),
}
# Ketua tim (bukan pengelola) hanya boleh dokumen ini, dan hanya berisi item timnya sendiri.
LEADER_TEMPLATES = frozenset({"BAST", "PROGRESS_SLIDES"})
PERIODIC = {
    "EXCEL_XLSX": ("PERIODIC_RECAP", periodic_xlsx, "builtin:periodic-xlsx-v1"),
    "PPTX": ("PERIODIC_SLIDES", periodic_pptx, "builtin:periodic-pptx-v1"),
}
MAX_PERIOD_DAYS = 31
MAX_PHOTOS_PER_POINT = 6
MAX_PHOTOS = 40
MAX_PHOTOS_TEAM_WEEK = 90  # ±3 foto × 30 pekerjaan seminggu
PHOTO_EDGE = 1280
# Status penugasan aset (enum asset_status_enum) dalam Bahasa Indonesia untuk dokumen cetak.
_ASSET_STATUS = {"loaned": "Dipinjam", "allocated": "Dialokasikan", "ready": "Siap", "returned": "Dikembalikan"}
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


def _asset_lines(rows: list[Any]) -> list[AssetLine]:
    """Baris SQL kendaraan/alat → model dokumen."""
    return [
        AssetLine(kind=r.kind, name=r.name or "-", code=r.code, holder=r.holder, work_date=r.work_date,
                  status=_ASSET_STATUS.get(r.status or "", r.status))
        for r in rows
    ]


def _slug(text: str | None) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text or "").strip("-")[:40] or "dokumen"


# Nama berkas unduhan yang informatif (dokumen baru); jenis lain tetap memakai kode templatnya.
FILE_LABEL = {"ORDER_SHEET": "Surat-tugas-order", "DAILY_REPORT": "Laporan-harian-tim"}


def file_name(record: Any) -> str:
    stamp = record.create_at.strftime("%Y%m%d-%H%M")
    label = FILE_LABEL.get(record.template_type, record.template_type)
    return f"{label}_{stamp}.{EXT.get(record.export_format, 'bin')}"


class ExportService:
    def __init__(self, repo: ExportRepository, orders: WorkCompletionService,
                 surveys: SurveyService | None = None) -> None:
        self.repo = repo
        self.orders = orders
        self.surveys = surveys

    # ── Laporan survei berformat baku (docs/37) ───────────────────────────────
    async def export_survey(self, user: CurrentUser, task_id: UUID) -> tuple[Any, bytes]:
        if self.surveys is None:  # pragma: no cover - dirakit di dependencies
            raise AppError("NOT_CONFIGURED", "Ekspor survei belum dirakit.", status=500)
        survey = await self.surveys.detail(user, task_id)
        if survey["state"] == "DRAFT":
            raise AppError("SURVEY_NOT_SUBMITTED", "Laporan tersedia setelah ketua tim mengirim survei.", status=409)
        content = build_survey_docx(await self._survey_doc(survey, user))
        fmt = survey["format"]
        key = (f"exports/survey/{task_id}/{jakarta_now():%Y%m%d-%H%M%S}_survey_{fmt.lower()}_"
               f"{_slug(survey['client_name'])}.docx")
        record = await self._store(user, key, content, "WORD_DOCX", source_type="WORK_COMPLETION",
                                   completion_id=survey["completion_id"], template_type=f"SURVEY_{fmt}",
                                   master=f"templates/survey_{fmt.lower()}.docx")
        return record, content

    async def preview_survey(self, user: CurrentUser, task_id: UUID) -> tuple[str, bytes]:
        """Pratinjau laporan survei untuk ketua tim & PM, kapan pun (juga sebelum dikirim). Tidak disimpan/dicatat.
        PDF bila LibreOffice tersedia di server, selain itu .docx."""
        if self.surveys is None:  # pragma: no cover - dirakit di dependencies
            raise AppError("NOT_CONFIGURED", "Ekspor survei belum dirakit.", status=500)
        survey = await self.surveys.detail(user, task_id)
        if not survey["points"]:
            raise AppError("NO_SURVEY_POINTS", "Belum ada titik survei untuk dipratinjau.", status=422)
        docx = build_survey_docx(await self._survey_doc(survey, user))
        pdf = await docx_to_pdf(docx)
        return ("PDF", pdf) if pdf else ("WORD_DOCX", docx)

    async def _survey_doc(self, s: dict[str, Any], user: CurrentUser) -> SurveyDoc:
        file_ids = [str(ph["file_id"]) for p in s["points"] for ph in p["photos"]]
        keys = await self.repo.image_keys([f for f in dict.fromkeys(file_ids) if _UUID.match(f)][:MAX_PHOTOS])
        images: dict[str, bytes] = {}
        for fid, key in keys.items():
            raw = storage.get_image_bytes(key)
            small = _shrink(raw) if raw else None
            if small:
                images[fid] = small
        roster = await self.repo.team_roster([str(s["team_id"])]) if s.get("team_id") else []
        leader = next((m.full_name for m in roster if m.is_leader), "")
        members = [m.full_name for m in roster]
        d = s["work_date"]
        date_text = tgl(d)
        names = [p["name"] for p in s["points"]]
        location = s.get("location") or "-"
        if s["format"] == "ACS":
            activities = [f"{s.get('purpose') or 'Assesment pemasangan ACS'} pada {location}"]
            default = (f"Assessment dilakukan pada tanggal {date_text.replace(' ', '-')} dengan diikuti oleh "
                       f"Team VTI ({', '.join(members) or leader}).")
        else:
            activities = ["Survey Lokasi", "Menentukan titik pemasangan: " + ", ".join(names)]
            default = (f"Berikut uraian hasil survey pemasangan {len(names)} titik di {location}. Survey dilakukan "
                       f"pada tanggal {date_text} oleh {s.get('team_name') or 'tim'} ({', '.join(members)}).")
        narrative = [t.strip() for t in (s.get("narrative") or default).split("\n\n") if t.strip()]
        points = []
        many_types = len({str(p["point_type_id"]) for p in s["points"]}) > 1
        type_slots = {str(t["work_type_id"]): [sl["name"] for sl in t["slots"]] for t in s["point_types"]}
        for p in s["points"]:
            lines = p["lines"]
            cable: dict[str, str] = {}
            for ln in lines:
                if ln["category"] == "KABEL" and ln["name"] in FO_COLUMNS:
                    cable[ln["name"]] = ln.get("notes") or "" if ln["name"] in ("Uplink Switch", "Remark") \
                        else str(ln["qty"])
            label = f"{p['name']} ({p['point_type_name']})" if many_types else p["name"]
            points.append(SurveyPointDoc(
                name=label, remarks=p["remarks"], status=p["point_status"],
                slots=type_slots.get(str(p["point_type_id"]), []),
                photos=[SurveyPhoto(ph.get("slot") or "", images[str(ph["file_id"])]) for ph in p["photos"]
                        if str(ph["file_id"]) in images],
                materials=[(ln["name"], ln["qty"], ln["unit"]) for ln in lines if ln["category"] == "MATERIAL"],
                needs=[ln["name"] for ln in lines if ln["category"] == "KEBUTUHAN"],
                cable=cable,
            ))
        # Layout otomatis: citra satelit + penanda titik (koordinat titik, bisa digeser PM/ketua tim di peta).
        auto = await asyncio.to_thread(render_point_map, [
            MapPoint(p["name"], float(p["site_lat"]), float(p["site_lng"]),
                     next((images[str(ph["file_id"])] for ph in p["photos"] if str(ph["file_id"]) in images), None),
                     status=p["point_status"])
            for p in s["points"] if p.get("site_lat") is not None and p.get("site_lng") is not None])
        return SurveyDoc(
            format=s["format"], client=s["client_name"], date_text=date_text,
            activity_date_text=date_text.replace(" ", "-") if s["format"] == "ACS" else date_text,
            location=location, purpose=s.get("purpose") or "-", activities=activities, narrative=narrative,
            auto_layout=auto, project_title=s.get("project_title") or "",
            points=points,
            bom=[(b["name"], b["qty"], b["unit"], b["group"]) for b in s["bom"]],
            team_name=s.get("team_name") or "", leader_name=leader, member_names=members,
            logos=await self._survey_logos_for(s, user),
        )

    async def _survey_logos_for(self, s: dict[str, Any], user: CurrentUser) -> dict[str, bytes]:
        """Logo kop survei: logo perusahaan diganti logo tim bila tim punya logo; sisanya logo organisasi."""
        logos = await asyncio.to_thread(branding.custom_logos, user.organization_id)
        team_logo = await self._team_logo([str(s["team_id"])]) if s.get("team_id") else None
        return {**logos, "company": team_logo} if team_logo else logos

    # ── Logo kop laporan survei ───────────────────────────────────────────────
    def survey_logos(self, user: CurrentUser) -> list[dict[str, Any]]:
        custom = branding.custom_logos(user.organization_id)
        return [{"role": role, **spec, "recommended_px": branding.standard_px(role), "custom": role in custom}
                for role, spec in branding.STANDARD.items()]

    def survey_logo_image(self, user: CurrentUser, role: str) -> bytes | None:
        return branding.custom_logos(user.organization_id).get(role)

    def set_survey_logo(self, user: CurrentUser, role: str, raw: bytes) -> list[dict[str, Any]]:
        if not storage.upload_file(branding.logo_key(user.organization_id, role), branding.normalize_upload(raw),
                                   "image/png"):
            raise AppError("STORAGE_UNAVAILABLE", "Penyimpanan berkas tidak tersedia.", status=503)
        return self.survey_logos(user)

    def reset_survey_logo(self, user: CurrentUser, role: str) -> list[dict[str, Any]]:
        storage.delete_object(branding.logo_key(user.organization_id, role))
        return self.survey_logos(user)

    # ── Dokumen order ─────────────────────────────────────────────────────────
    async def _order_scope(self, user: CurrentUser, completion_id: UUID,
                           template: str | None) -> tuple[dict[str, Any], set[str] | None]:
        """(order, team_ids). team_ids None = seluruh order (pengelola); set = ketua tim, hanya item tim-tim ini.
        `template` None = daftar/riwayat (tanpa pembatasan templat)."""
        order, full = await self.orders.export_access(user, completion_id)
        if full:
            return order, None
        if template is not None and template not in LEADER_TEMPLATES:
            raise ForbiddenError("Ketua tim hanya dapat mengunduh BAST dan slide progres untuk timnya.")
        return order, await self.repo.led_team_ids(user.employee_id)

    async def export_completion(self, user: CurrentUser, completion_id: UUID, template: str) -> tuple[Any, bytes]:
        order, team_ids = await self._order_scope(user, completion_id, template)
        export_format, build, master = COMPLETION_TEMPLATES[template]
        if template == "BAST_PDF" and not order.get("signature_hash"):
            raise AppError("NOT_SIGNED", "PDF resmi tersedia setelah serah terima disetujui PM.", status=409)
        report = await self._completion_report(order, user, team_ids)
        if template == "SURVEY_REPORT" and not report.survey_points:
            raise AppError("NO_SURVEY_ITEMS", "Order ini belum punya item fase Survei.", status=422)
        content = build(report)
        key = (f"exports/work-completion/{completion_id}/{jakarta_now():%Y%m%d-%H%M%S}_"
               f"{template.lower()}_{_slug(order.get('client_name'))}.{EXT[export_format]}")
        record = await self._store(user, key, content, export_format, source_type="WORK_COMPLETION",
                                   completion_id=completion_id, template_type=template, master=master)
        return record, content

    async def list_for_completion(self, user: CurrentUser, completion_id: UUID) -> list[Any]:
        _, team_ids = await self._order_scope(user, completion_id, None)
        rows = await self.repo.list_exports(completion_id=completion_id)
        if team_ids is not None:  # ketua hanya melihat riwayat ekspornya sendiri
            rows = [r for r in rows if str(r.generated_by_id) == str(user.employee_id)]
        return rows

    # ── Laporan harian satu jadwal (cetak per hari) ──────────────────────────
    async def export_daily_report(self, user: CurrentUser, daily_plan_id: UUID) -> tuple[Any, bytes]:
        await check_daily_access(self.repo.db, daily_plan_id, user, DailyNeed.VIEW)  # tak terlihat → 404
        header = await self.repo.daily_header(daily_plan_id)
        if header is None:
            raise NotFoundError("Jadwal harian")
        items = await self.repo.daily_items(daily_plan_id)
        points, _ = await self._points(items, [], [], MAX_PHOTOS)
        report = DailyReport(
            team_name=header.team_name, division_name=header.division_name, work_date=header.work_date,
            site_name=header.site_name, status=header.status, leader_name=header.leader_name, points=points,
            roster=await self.repo.team_roster([str(header.team_id)]), summary=header.summary,
            obstacles=header.obstacles, generated_by=await self._printer(user), generated_at=jakarta_now(),
            report_submitted_at=header.report_submitted_at,
            team_logo=await self._team_logo([str(header.team_id)]),
            assets=_asset_lines(await self.repo.daily_assets(daily_plan_id)),
        )
        content = daily_report_docx(report)
        key = (f"exports/daily-report/{daily_plan_id}/{jakarta_now():%Y%m%d-%H%M%S}_daily_report_"
               f"{_slug(header.team_name)}_{header.work_date:%Y%m%d}.docx")
        record = await self._store(user, key, content, "WORD_DOCX", source_type="WORK_PLAN_DAILY",
                                   template_type="DAILY_REPORT", master="builtin:daily-report-docx-v1",
                                   daily_plan_id=daily_plan_id)
        return record, content

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
            generated_by=await self._printer(user), generated_at=jakarta_now(),
        )
        content = build(report)
        key = (f"exports/periodic/{division_id}/{start:%Y%m%d}-{end:%Y%m%d}_{jakarta_now():%H%M%S}_"
               f"{template_type.lower()}.{EXT[export_format]}")
        record = await self._store(user, key, content, export_format, source_type="WORK_PLAN_PERIODIC",
                                   template_type=template_type, master=master, period=(start, end))
        return record, content

    async def list_periodic(self, user: CurrentUser) -> list[Any]:
        sees_all = is_admin(user) or user.has_role("OPERATIONAL_MANAGER")
        if not sees_all and not user.employee_id:
            return []
        return await self.repo.list_exports(generated_by=None if sees_all else user.employee_id)

    # ── Unduh ulang dari registri ────────────────────────────────────────────
    async def download(self, user: CurrentUser, export_id: UUID) -> tuple[Any, bytes]:
        record = await self.repo.get_export(export_id)
        if record is None:
            raise NotFoundError("Dokumen")
        if record.completion_id is not None:
            # tak terlihat → 404; ketua tim hanya berkas buatannya sendiri (berkas PM memuat seluruh order)
            _, team_ids = await self._order_scope(user, record.completion_id, record.template_type)
            if team_ids is not None and str(record.generated_by_id) != str(user.employee_id):
                raise NotFoundError("Dokumen")
        elif not (is_admin(user) or user.has_role("OPERATIONAL_MANAGER")
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
                     period: tuple[date, date] | None = None, daily_plan_id: UUID | None = None) -> Any:
        if not user.employee_id:
            raise ForbiddenError("Akun ini belum tertaut ke data karyawan.")
        if not storage.upload_file(key, content, MIME[export_format]):
            raise AppError("STORAGE_UNAVAILABLE", "Penyimpanan berkas sedang tidak tersedia. Coba lagi.", status=503)
        return await self.repo.insert_export(
            source_type=source_type, completion_id=completion_id, period_start=period[0] if period else None,
            period_end=period[1] if period else None, template_type=template_type, master_template=master,
            export_format=export_format, storage_key=key, generated_by=user.employee_id,
            daily_plan_id=daily_plan_id,
        )

    async def _points(
        self, items: list[Any], bom: list[dict[str, Any]], extra_refs: list[dict[str, str | None]], max_photos: int,
    ) -> tuple[list[ReportPoint], Callable[[list[dict[str, str | None]], str], list[ReportPhoto]]]:
        """Item → ReportPoint lengkap dengan foto (diperkecil) + label syarat fotonya."""
        item_refs = {str(i.item_id): photo_refs(i.photos)[:MAX_PHOTOS_PER_POINT] for i in items}
        all_refs = [r for refs in item_refs.values() for r in refs] + extra_refs
        file_ids = list(dict.fromkeys(r["file_id"] for r in all_refs if r["file_id"] and _UUID.match(r["file_id"])))
        keys = await self.repo.image_keys(file_ids[:max_photos])
        names = await self.repo.requirement_names(
            list({str(r["requirement_id"]) for r in all_refs if r.get("requirement_id")}))
        images: dict[str, bytes] = {}
        for fid, key in keys.items():
            raw = storage.get_image_bytes(key)
            small = _shrink(raw) if raw else None
            if small:
                images[fid] = small

        def photos(refs: list[dict[str, str | None]], fallback: str) -> list[ReportPhoto]:
            return [ReportPhoto(names.get(str(r.get("requirement_id")), fallback), images[str(r["file_id"])])
                    for r in refs if str(r["file_id"]) in images]

        points = [
            ReportPoint(
                item_id=str(i.item_id), title=i.title, phase=i.task_phase, status=i.status, work_date=i.work_date,
                team_name=i.team_name, location=i.location_name or i.site_name or "", lat=i.site_lat, lng=i.site_lng,
                target=i.target_qty, completed=i.completed_qty, progress=i.progress_percent, notes=i.notes,
                delay_reason=i.delay_reason, assignees=i.assignees, work_type=i.work_type_name,
                photos=photos(item_refs[str(i.item_id)], "Foto pekerjaan"),
                bom=[b for b in bom if str(b.get("work_plan_item_id")) == str(i.item_id)],
            )
            for i in items
        ]
        return points, photos

    # ── Laporan mingguan tim (ketua/anggota tim, atau PM/OM divisinya) ──────
    async def export_team_week(self, user: CurrentUser, team_id: UUID, start: date) -> tuple[Any, bytes]:
        team = await self.repo.team_info(team_id)
        if team is None:
            raise NotFoundError("Tim")
        in_team = user.employee_id is not None and await self.repo.is_team_member(team_id, user.employee_id)
        # HR/GA (ADMIN_HR_GA) boleh melihat seperti laporan harian (akses baca, konsisten dengan daily-report).
        if not (in_team or is_admin(user) or user.has_role("ADMIN_HR_GA")):
            await check_division_manager(self.repo.db, team.division_id, user)
        end = start + timedelta(days=6)
        items = await self.repo.team_week_items(team_id, start, end)
        if not items:
            raise AppError("NO_WORK", "Belum ada pekerjaan tim ini pada minggu tersebut.", status=422)
        points, _ = await self._points(items, [], [], MAX_PHOTOS_TEAM_WEEK)
        report = TeamWeekReport(
            team_name=team.name, division_name=team.division_name, start=start, end=end, points=points,
            roster=await self.repo.team_roster([str(team_id)]), generated_by=await self._printer(user),
            generated_at=jakarta_now(), team_logo=await self._team_logo([str(team_id)]),
            assets=_asset_lines(await self.repo.team_week_assets(team_id, start, end)),
        )
        content = team_week_pptx(report)
        key = f"exports/team-week/{team_id}/{start:%Y%m%d}_{jakarta_now():%H%M%S}_team_week.pptx"
        record = await self._store(user, key, content, "PPTX", source_type="WORK_PLAN_PERIODIC",
                                   template_type="TEAM_WEEK_SLIDES", master="builtin:team-week-pptx-v1",
                                   period=(start, end))
        return record, content

    async def _team_logo(self, team_ids: list[str]) -> bytes | None:
        """Logo tim untuk kop dokumen. Hanya bila dokumen memuat satu tim; lebih dari satu tim → logo default."""
        ids = list(dict.fromkeys(t for t in team_ids if t))
        if len(ids) != 1:
            return None
        key = (await self.repo.team_logo_keys(ids)).get(ids[0])
        return await asyncio.to_thread(branding.team_logo_or_default, ids[0], key)

    async def _printer(self, user: CurrentUser) -> str:
        """Nama pencetak untuk dokumen (bukan email). Tanpa data karyawan → "-"."""
        name = await self.repo.employee_name(user.employee_id) if user.employee_id else None
        return name or "-"

    async def _completion_report(self, order: dict[str, Any], user: CurrentUser,
                                 team_ids: set[str] | None = None) -> CompletionReport:
        items = await self.repo.completion_items(order["completion_id"])
        if team_ids is not None:  # ketua tim: hanya item timnya (roster ikut terbatas)
            items = [i for i in items if str(i.team_id) in team_ids]
            if not items:
                raise ForbiddenError("Order ini tidak memiliki pekerjaan untuk tim yang Anda pimpin.")
        order_refs = photo_refs(order.get("realization_photos_json"))[:MAX_PHOTOS_PER_POINT * 2]
        bom = list(order.get("bom_items") or [])
        points, photos = await self._points(items, bom, order_refs, MAX_PHOTOS)
        roster = await self.repo.team_roster(list(dict.fromkeys(str(i.team_id) for i in items)))
        leader_key, pm_key = order.get("leader_signature_path"), order.get("pm_signature_path")
        # Peta lokasi: penanda per titik berkoordinat (hijau = selesai). Tanpa koneksi → None (ditandai di dokumen).
        marks = [MapPoint(p.title, float(p.lat), float(p.lng), next((ph.image for ph in p.photos), None),
                          status="EXISTING" if p.status == "DONE" else "PROPOSED")
                 for p in points if p.lat is not None and p.lng is not None]
        # Lokasi order sendiri ikut ditandai (penanda terakhir: nomor titik pada tabel tetap sesuai urutan).
        if order.get("site_lat") is not None and order.get("site_lng") is not None:
            marks.append(MapPoint("Lokasi order", float(order["site_lat"]), float(order["site_lng"]), None,
                                  status="PROPOSED"))
        map_image = await asyncio.to_thread(render_point_map, marks) if marks else None
        return CompletionReport(
            order=order, points=points, roster=roster, bom=bom, generated_by=await self._printer(user),
            generated_at=jakarta_now(), verify_url=verify_url(order), photos=photos(order_refs, "Foto realisasi"),
            leader_signature=storage.get_image_bytes(leader_key) if leader_key else None,
            pm_signature=storage.get_image_bytes(pm_key) if pm_key else None,
            map_image=map_image, has_coordinates=bool(marks),
            team_logo=await self._team_logo([str(i.team_id) for i in items]),
        )
