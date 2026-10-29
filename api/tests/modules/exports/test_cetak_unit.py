"""
api/tests/modules/exports/test_cetak_unit.py
Uji unit dokumen cetak (tanpa DB, tanpa jaringan): surat tugas (ORDER_SHEET), laporan harian per jadwal, peta
lokasi di BAST (tile di-monkeypatch) dan aturan akses ekspor laporan harian.
"""

from __future__ import annotations

import io
import os
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import docx
import pytest
from PIL import Image

from app.core.errors import ForbiddenError, NotFoundError
from app.modules.exports.services import export_service as es
from app.modules.exports.services.builders.docx_builders import bast_docx, daily_report_docx, order_sheet_docx
from app.modules.exports.services.builders.model import (
    CompletionReport,
    DailyReport,
    ReportPhoto,
    ReportPoint,
)
from app.modules.exports.services.builders.model import (
    tgl as tgl_text,
)
from app.shared.documents import static_map as sm


def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (20, 40, 60)).save(buf, "JPEG")
    return buf.getvalue()


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 20), (200, 30, 30)).save(buf, "PNG")
    return buf.getvalue()


def _text(content: bytes) -> str:
    d = docx.Document(io.BytesIO(content))
    cells = [c.text for t in d.tables for r in t.rows for c in r.cells]
    return "\n".join([p.text for p in d.paragraphs] + cells)


def _images(content: bytes) -> int:
    return len(docx.Document(io.BytesIO(content)).inline_shapes)


ORDER = {
    "completion_id": "5b8d0000-0000-4000-a000-000000000002",
    "order_number": "PHR-02",
    "client_name": "PHR",
    "project_title": "Pemasangan CCTV Minas",
    "division_name": "MEP",
    "pm_name": "Dedi PM",
    "site_address": "Minas, Riau",
    "start_work_date": date(2026, 11, 2),
    "end_work_date": date(2026, 11, 20),
    "total_target_unit": 3,
    "unit_measure": "Titik",
    "completed_target_unit": 0,
    "summary_notes": None,
    "signature_hash": None,
    "bom_items": [
        {
            "material_code": "CAM",
            "material_name": "Kamera IP",
            "estimated_qty": 3,
            "actual_qty": 0,
            "unit": "unit",
            "work_plan_item_id": "i1",
        }
    ],
}


def _point(
    title: str,
    *,
    lat: float | None = None,
    lng: float | None = None,
    status: str = "TODO",
    notes: str | None = None,
    delay: str | None = None,
    photos: list[ReportPhoto] | None = None,
    day: int = 2,
) -> ReportPoint:
    return ReportPoint(
        "i-" + title,
        title,
        "INSTALLATION",
        status,
        date(2026, 11, day),
        "Tim MEP",
        "Pos Utara",
        lat,
        lng,
        1,
        0,
        0,
        notes,
        delay,
        "Riko",
        "Instalasi",
        photos or [],
        [],
    )


def _completion(
    points: list[ReportPoint], *, map_image: bytes | None = None, has_coordinates: bool = False
) -> CompletionReport:
    return CompletionReport(
        {**ORDER},
        points,
        [],
        ORDER["bom_items"],
        "pm@x",
        datetime(2026, 11, 1, tzinfo=UTC),
        None,
        [],
        None,
        None,
        map_image=map_image,
        has_coordinates=has_coordinates,
    )


# ── Surat tugas (ORDER_SHEET) ────────────────────────────────────────────────


def test_order_sheet_is_a_printable_assignment_without_signatures():
    content = order_sheet_docx(_completion([_point("Titik A"), _point("Titik B")]))
    text = _text(content)
    assert "SURAT TUGAS PEKERJAAN" in text
    assert "Pemasangan CCTV Minas" in text and "Dedi PM" in text and "Minas, Riau" in text
    assert "Titik A" in text and "Kamera IP" in text
    assert "tidak memerlukan tanda tangan" in text
    assert "Dibuat oleh (Ketua Tim)" not in text and "Disetujui oleh" not in text  # tanpa blok pengesahan


def test_order_sheet_without_items_still_renders():
    text = _text(order_sheet_docx(_completion([])))
    assert "Rincian titik belum dibuat." in text


# ── Laporan harian per jadwal ────────────────────────────────────────────────


def test_daily_report_lists_items_status_delay_and_leader_report():
    report = DailyReport(
        team_name="Tim MEP",
        division_name="MEP",
        work_date=date(2026, 11, 3),
        site_name="Pos Utara",
        status="ONGOING",
        leader_name="Agus",
        points=[
            _point("Instalasi 01", status="DONE", notes="Selesai rapi"),
            _point("Instalasi 02", status="PENDING_ROLLOVER", delay="Hujan deras"),
        ],
        roster=[SimpleNamespace(full_name="Agus", is_leader=True), SimpleNamespace(full_name="Riko", is_leader=False)],
        summary="Pekerjaan berjalan sesuai rencana",
        obstacles="Akses jalan licin",
        generated_by="pm@x",
        generated_at=datetime(2026, 11, 3, 17, tzinfo=UTC),
        report_submitted_at=datetime(2026, 11, 3, 16, tzinfo=UTC),
    )
    text = _text(daily_report_docx(report))
    assert "LAPORAN HARIAN TIM" in text
    assert "Agus" in text and "Riko" in text
    assert "Instalasi 01" in text and "Selesai rapi" in text
    assert "Minta pindah hari" in text and "Tunda: Hujan deras" in text
    assert "Pekerjaan berjalan sesuai rencana" in text and "Akses jalan licin" in text


def test_daily_report_without_leader_report_says_so():
    report = DailyReport(
        "Tim MEP",
        "MEP",
        date(2026, 11, 3),
        None,
        "APPROVED",
        "-",
        [],
        [],
        None,
        None,
        "pm@x",
        datetime(2026, 11, 3, tzinfo=UTC),
    )
    text = _text(daily_report_docx(report))
    assert "Belum ada laporan ringkasan dari ketua tim." in text
    assert "Belum ada item pekerjaan pada jadwal ini." in text


# ── Peta lokasi & ringkasan harian di BAST ───────────────────────────────────


def test_bast_shows_daily_summary_per_day_and_map_when_available():
    points = [
        _point("Survei A", lat=1.4, lng=101.4, status="DONE", day=2),
        _point("Instalasi B", lat=1.5, lng=101.5, status="IN_PROGRESS", day=3),
    ]
    content = bast_docx(_completion(points, map_image=_png(), has_coordinates=True))
    text = _text(content)
    assert "Ringkasan Laporan Harian" in text and "Peta Lokasi" in text
    assert _images(content) >= 1  # peta tertanam sebagai gambar


def test_bast_says_map_unavailable_without_connection():
    points = [_point("Survei A", lat=1.4, lng=101.4)]
    text = _text(bast_docx(_completion(points, map_image=None, has_coordinates=True)))
    assert "Peta tidak tersedia (tanpa koneksi ke citra satelit)." in text


def test_bast_keeps_map_page_with_placeholder_without_coordinates():
    text = _text(bast_docx(_completion([_point("Tanpa koordinat")])))
    assert "Peta Lokasi" in text
    assert "Koordinat lokasi belum diisi." in text
    assert "Ringkasan Laporan Harian" in text


def test_map_renders_with_monkeypatched_tiles(monkeypatch):
    solid = Image.new("RGB", (256, 256), (90, 120, 90))
    monkeypatch.setattr(sm, "_tile", lambda z, x, y, client: solid)
    png = sm.render_point_map(
        [sm.MapPoint("A", -6.2, 106.8, None, "EXISTING"), sm.MapPoint("B", -6.21, 106.82, _jpeg(), "PROPOSED")]
    )
    assert png is not None
    assert Image.open(io.BytesIO(png)).size == sm.SIZE


def test_map_returns_none_when_no_tile_available(monkeypatch):
    monkeypatch.setattr(sm, "_tile", lambda z, x, y, client: None)
    assert sm.render_point_map([sm.MapPoint("A", -6.2, 106.8)]) is None


@pytest.mark.skipif(
    os.environ.get("RUN_NETWORK_TESTS") != "1",
    reason="Uji manual: butuh internet. Jalankan dengan RUN_NETWORK_TESTS=1.",
)
def test_map_downloads_real_satellite_tiles_manual():  # pragma: no cover - manual
    png = sm.render_point_map(
        [sm.MapPoint("A", -6.2, 106.8, None, "EXISTING"), sm.MapPoint("B", -6.21, 106.82, None, "PROPOSED")]
    )
    assert png is not None and png[:8] == b"\x89PNG\r\n\x1a\n"


# ── Layanan: peta di _completion_report & laporan harian ─────────────────────


def _svc(items: list | None = None, header: object | None = None) -> es.ExportService:
    orders = MagicMock()
    orders.get_order_detail = AsyncMock(return_value={**ORDER})
    orders.export_access = AsyncMock(return_value=({**ORDER}, True))  # pengelola = akses penuh
    repo = MagicMock()
    repo.db = MagicMock()
    repo.completion_items = AsyncMock(return_value=items or [])
    repo.daily_items = AsyncMock(return_value=items or [])
    repo.daily_header = AsyncMock(return_value=header)
    repo.team_roster = AsyncMock(return_value=[])
    repo.team_logo_keys = AsyncMock(return_value={})  # tanpa logo tim: dokumen memakai logo default
    repo.image_keys = AsyncMock(return_value={})
    repo.requirement_names = AsyncMock(return_value={})
    repo.employee_name = AsyncMock(return_value="Pengguna Uji")
    repo.insert_export = AsyncMock(
        return_value=SimpleNamespace(
            export_id="e1",
            source_type="WORK_PLAN_DAILY",
            completion_id=None,
            daily_plan_id="d1",
            period_start_date=None,
            period_end_date=None,
            template_type="DAILY_REPORT",
            export_format="WORD_DOCX",
            file_output_url="k",
            generated_by_id="u1",
            generated_by_name="PM",
            create_at=datetime(2026, 11, 3, tzinfo=UTC),
        )
    )
    return es.ExportService(repo, orders)


def _row(**kw) -> SimpleNamespace:
    base = {
        "item_id": "i1",
        "title": "Instalasi 01",
        "task_phase": "INSTALLATION",
        "status": "DONE",
        "location_name": "Pos",
        "site_name": None,
        "site_lat": 1.4,
        "site_lng": 101.4,
        "target_qty": 1.0,
        "completed_qty": 1.0,
        "progress_percent": 100.0,
        "notes": None,
        "delay_reason": None,
        "photos": None,
        "work_type_name": "Instalasi",
        "work_date": date(2026, 11, 3),
        "team_name": "Tim MEP",
        "team_id": "t1",
        "assignees": "Riko",
        "daily_plan_id": "d1",
    }
    base.update(kw)
    return SimpleNamespace(**base)


USER = SimpleNamespace(employee_id="e1", email="pm@x", role="PROJECT_MANAGER", organization_id="o1")


@pytest.fixture(autouse=True)
def _no_storage(monkeypatch):
    """Penyimpanan berkas dibuat palsu: uji ini tak menyentuh MinIO/disk."""
    monkeypatch.setattr(es.storage, "upload_file", lambda *a, **k: True)


@pytest.mark.anyio
async def test_completion_report_adds_map_for_geotagged_items(monkeypatch):
    seen: list[list] = []

    def fake_map(points):
        seen.append(points)
        return _png()

    monkeypatch.setattr(es, "render_point_map", fake_map)
    rows = [_row(item_id="a", status="DONE"), _row(item_id="b", status="TODO", site_lat=None, site_lng=None)]
    report = await _svc(rows)._completion_report({**ORDER}, USER)
    assert report.has_coordinates is True and report.map_image == _png()
    assert [m.status for m in seen[0]] == ["EXISTING"]  # hanya titik berkoordinat; DONE → hijau


@pytest.mark.anyio
async def test_completion_report_skips_map_without_coordinates(monkeypatch):
    monkeypatch.setattr(es, "render_point_map", lambda pts: pytest.fail("peta tidak perlu dibuat"))
    report = await _svc([_row(site_lat=None, site_lng=None)])._completion_report({**ORDER}, USER)
    assert report.has_coordinates is False and report.map_image is None


@pytest.mark.anyio
async def test_order_sheet_export_uses_docx_and_no_signature_gate():
    svc = _svc([])
    _, content = await svc.export_completion(USER, ORDER["completion_id"], "ORDER_SHEET")
    assert "SURAT TUGAS PEKERJAAN" in _text(content)


@pytest.mark.anyio
async def test_daily_report_export_is_stored_with_its_schedule(monkeypatch):
    monkeypatch.setattr(es.storage, "upload_file", lambda *a, **k: True)
    header = SimpleNamespace(
        daily_plan_id="d1",
        team_id="t1",
        work_date=date(2026, 11, 3),
        site_name="Pos Utara",
        status="ONGOING",
        team_name="Tim MEP",
        division_name="MEP",
        leader_name="Agus",
        summary="Ringkasan",
        obstacles=None,
        report_submitted_at=None,
    )
    svc = _svc([_row()], header)
    monkeypatch.setattr(es, "check_daily_access", AsyncMock(return_value=None))
    _, content = await svc.export_daily_report(USER, "d1")
    assert "LAPORAN HARIAN TIM" in _text(content)
    assert svc.repo.insert_export.await_args.kwargs["daily_plan_id"] == "d1"


@pytest.mark.anyio
async def test_daily_report_hidden_schedule_is_not_found_or_forbidden(monkeypatch):
    svc = _svc([], None)
    monkeypatch.setattr(es, "check_daily_access", AsyncMock(side_effect=NotFoundError("Jadwal harian")))
    with pytest.raises(NotFoundError):
        await svc.export_daily_report(USER, "d1")
    monkeypatch.setattr(es, "check_daily_access", AsyncMock(side_effect=ForbiddenError("x")))
    with pytest.raises(ForbiddenError):
        await svc.export_daily_report(USER, "d1")


def test_bast_map_legend_uses_same_terms_as_the_map():
    points = [_point("Survei A", lat=1.4, lng=101.4, status="DONE", day=2)]
    text = _text(bast_docx(_completion(points, map_image=_png(), has_coordinates=True)))
    assert "Existing (sudah terpasang)" in text and "Usulan pemasangan baru" in text


# ── Uji tambahan B7: peta order, jadwal, koordinat, dan status berbahasa Indonesia ─────────────


def test_bast_daily_summary_covers_every_schedule_day_of_the_order():
    text = _text(bast_docx(_completion([_point("Survei A", day=2)])))
    for day in (date(2026, 11, 2), date(2026, 11, 5), date(2026, 11, 20)):
        assert tgl_text(day) in text, tgl_text(day)
    assert "Tidak ada pekerjaan tercatat." in text


def test_bast_and_order_sheet_print_order_coordinates():
    order = {**ORDER, "site_lat": -6.1944, "site_lng": 106.8229}
    report = _completion([_point("Survei A", day=2)])
    report.order.update(order)
    assert "-6.194400, 106.822900" in _text(bast_docx(report))
    assert "-6.194400, 106.822900" in _text(order_sheet_docx(report))


def test_order_sheet_schedule_falls_back_to_item_dates_not_dashes():
    report = _completion([_point("Survei A", day=2), _point("Survei B", day=5)])
    report.order.update({"start_work_date": None, "end_work_date": None})
    text = _text(order_sheet_docx(report))
    assert "2 November 2026 s.d. 5 November 2026" in text
    assert "- s.d. -" not in text


def test_daily_report_prints_plan_status_in_indonesian():
    report = DailyReport("Tim MEP", "MEP", date(2026, 11, 3), None, "APPROVED", "Agus", [], [], None, None,
                         "Budi", datetime(2026, 11, 3, tzinfo=UTC))
    text = _text(daily_report_docx(report))
    assert "Disetujui" in text and "APPROVED" not in text


@pytest.mark.anyio
async def test_completion_map_marks_the_order_site_even_without_item_coordinates(monkeypatch):
    seen: list[list] = []
    monkeypatch.setattr(es, "render_point_map", lambda points: seen.append(points) or _png())
    rows = [_row(item_id="a", site_lat=None, site_lng=None)]
    order = {**ORDER, "site_lat": -6.1944, "site_lng": 106.8229}
    report = await _svc(rows)._completion_report(order, USER)
    assert report.has_coordinates is True and report.map_image == _png()
    assert [m.label for m in seen[0]] == ["Lokasi order"]
