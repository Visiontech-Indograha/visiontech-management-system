"""
api/tests/modules/exports/test_export_unit.py
Uji unit Milestone 8 tanpa DB: builder dokumen (DOCX/XLSX/PPTX), sidik BAST, tanda tangan PNG, dan aturan ekspor.
"""
from __future__ import annotations

import base64
import io
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import docx
import pytest
from openpyxl import load_workbook
from PIL import Image
from pptx import Presentation

from app.core.errors import AppError, ValidationError
from app.modules.exports.repositories.export_repository import photo_refs
from app.modules.exports.services import export_service as es
from app.modules.exports.services.builders.docx_builders import bast_docx, survey_report_docx
from app.modules.exports.services.builders.model import CompletionReport, PeriodicReport, ReportPhoto, ReportPoint
from app.modules.exports.services.builders.office_builders import completion_pptx, completion_xlsx, periodic_xlsx
from app.modules.work_completion.services.work_completion_service import _decode_png, completion_fingerprint


def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (20, 40, 60)).save(buf, "JPEG")
    return buf.getvalue()


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (40, 20), (0, 0, 0, 0)).save(buf, "PNG")
    return buf.getvalue()


ORDER = {
    "completion_id": "5b8d0000-0000-4000-a000-000000000001", "order_number": "PHR-01", "client_name": "PHR",
    "project_title": "New CCTV MGT Minas", "site_address": "Minas", "total_target_unit": 3, "unit_measure": "Titik",
    "completed_target_unit": 1, "summary_notes": "Survei selesai", "obstacles": None,
    "realization_photos_json": [], "leader_signer_id": "e1", "leader_signed_at": datetime(2026, 9, 16, 9, tzinfo=UTC),
    "pm_signer_id": "e2", "pm_signed_at": datetime(2026, 9, 16, 15, tzinfo=UTC), "signature_hash": "ab" * 32,
    "bom_items": [{"material_code": "FO", "material_name": "Kabel FO", "estimated_qty": 450, "actual_qty": 430,
                   "unit": "m", "work_plan_item_id": "i1"}],
}


def _report() -> CompletionReport:
    survey = ReportPoint("i1", "Survei Titik 03", "SURVEY", "DONE", date(2026, 9, 14), "Tim MEP", "Pos Utara",
                         1.47, 101.45, 1, 1, 100, "Butuh tiang 6 m", None, "Riko", "Survei",
                         [ReportPhoto("Posisi", _jpeg()), ReportPhoto("View", _jpeg())], ORDER["bom_items"])
    install = ReportPoint("i2", "Instalasi 03", "INSTALLATION", "IN_PROGRESS", date(2026, 9, 15), "Tim MEP",
                          "Pos Utara", None, None, 1, 0, 0, None, None, "", "Instalasi")
    roster = [SimpleNamespace(full_name="Agus", employee_no="VT-6", is_leader=True, team_name="Tim MEP")]
    return CompletionReport(dict(ORDER), [survey, install], roster, ORDER["bom_items"], "pm@x",
                            datetime(2026, 9, 17, tzinfo=UTC), "http://v/verify", [], _png(), _png())


def _text(content: bytes) -> str:
    d = docx.Document(io.BytesIO(content))
    cells = [c.text for t in d.tables for r in t.rows for c in r.cells]
    return "\n".join([p.text for p in d.paragraphs] + cells)


def test_survey_report_follows_reference_outline():
    text = _text(survey_report_docx(_report()))
    for section in ("1. Informasi Survei", "2. Jadwal Survei", "3. Uraian Aktivitas & Tim", "4. Layout Titik",
                    "5. Kebutuhan Instalasi per Titik", "6. Dokumentasi per Titik", "7. Bill of Material (Estimasi)",
                    "8. Penutup"):
        assert section in text
    assert "Survei Titik 03" in text and "Instalasi 03" not in text  # hanya item fase SURVEY
    assert "Keterangan: Butuh tiang 6 m" in text
    assert "SHA-256" in text


def test_bast_docx_lists_points_bom_and_signers():
    text = _text(bast_docx(_report()))
    assert "BERITA ACARA SERAH TERIMA PEKERJAAN" in text
    assert "Instalasi 03" in text and "Kabel FO" in text
    assert "Ketua Tim" in text and "Project Manager" in text


def test_office_builders_produce_valid_files():
    wb = load_workbook(io.BytesIO(completion_xlsx(_report())))
    assert wb.sheetnames == ["BoQ", "Titik"]
    assert wb["BoQ"]["C5"].value == "Kabel FO" and wb["BoQ"]["G5"].value == -20
    assert len(Presentation(io.BytesIO(completion_pptx(_report()))).slides) >= 4
    meal = [SimpleNamespace(employee_no="VT-7", full_name="Riko", in_city_days=2, out_city_days=1,
                            total_amount=135000.0, pending_days=0)]
    per = PeriodicReport("MEP", date(2026, 9, 14), date(2026, 9, 20), [], [], meal, "pm",
                         datetime(2026, 9, 21, tzinfo=UTC))
    wb = load_workbook(io.BytesIO(periodic_xlsx(per)))
    assert wb.sheetnames == ["Jadwal", "BoQ", "Uang Makan"]
    assert wb["Uang Makan"]["E6"].value == 135000.0  # baris TOTAL


def test_fingerprint_changes_when_content_or_signature_changes():
    base = completion_fingerprint(ORDER, b"L", b"P")
    assert base == completion_fingerprint(dict(ORDER), b"L", b"P")
    assert base != completion_fingerprint({**ORDER, "summary_notes": "diubah"}, b"L", b"P")
    changed_bom = {**ORDER, "bom_items": [{**ORDER["bom_items"][0], "actual_qty": 431}]}
    assert base != completion_fingerprint(changed_bom, b"L", b"P")
    assert base != completion_fingerprint(ORDER, b"L", b"PALSU")


def test_signature_must_be_small_png():
    png = _png()
    assert _decode_png("data:image/png;base64," + base64.b64encode(png).decode()) == png
    with pytest.raises(ValidationError):
        _decode_png(base64.b64encode(_jpeg()).decode())
    with pytest.raises(ValidationError):
        _decode_png("bukan-base64!!")


def test_photo_refs_accepts_v2_objects_and_legacy_ids():
    assert photo_refs([{"file_id": "a", "requirement_id": "r"}, "b", {"x": 1}]) == [
        {"file_id": "a", "requirement_id": "r"}, {"file_id": "b", "requirement_id": None}]
    assert photo_refs('[{"file_id": "c"}]') == [{"file_id": "c", "requirement_id": None}]


def _service(order: dict) -> es.ExportService:
    orders = MagicMock()
    orders.get_order_detail = AsyncMock(return_value=order)
    orders.export_access = AsyncMock(return_value=(order, True))  # pengelola = akses penuh
    repo = MagicMock()
    repo.completion_items = AsyncMock(return_value=[])
    repo.team_roster = AsyncMock(return_value=[])
    repo.image_keys = AsyncMock(return_value={})
    repo.requirement_names = AsyncMock(return_value={})
    repo.employee_name = AsyncMock(return_value="Pengguna Uji")
    return es.ExportService(repo, orders)


@pytest.mark.anyio
async def test_official_pdf_requires_pm_signature():
    user = SimpleNamespace(employee_id="e1", email="pm@x", role="PROJECT_MANAGER")
    with pytest.raises(AppError) as err:
        await _service({**ORDER, "signature_hash": None}).export_completion(user, ORDER["completion_id"], "BAST_PDF")
    assert err.value.code == "NOT_SIGNED"


@pytest.mark.anyio
async def test_survey_report_requires_survey_items():
    user = SimpleNamespace(employee_id="e1", email="pm@x", role="PROJECT_MANAGER")
    with pytest.raises(AppError) as err:
        await _service(dict(ORDER)).export_completion(user, ORDER["completion_id"], "SURVEY_REPORT")
    assert err.value.code == "NO_SURVEY_ITEMS"


@pytest.mark.anyio
async def test_periodic_range_is_limited():
    user = SimpleNamespace(employee_id="e1", email="pm@x", role="PROJECT_MANAGER")
    svc = _service(dict(ORDER))
    with pytest.raises(ValidationError):
        await svc.export_periodic(user, ORDER["completion_id"], date(2026, 9, 20), date(2026, 9, 1), "EXCEL_XLSX")
    with pytest.raises(ValidationError):
        await svc.export_periodic(user, ORDER["completion_id"], date(2026, 8, 1), date(2026, 9, 30), "PPTX")



async def test_printed_by_shows_employee_name_not_email():
    svc = es.ExportService(repo=MagicMock(), orders=MagicMock())
    svc.repo.employee_name = AsyncMock(return_value="Budi Santoso")
    user = SimpleNamespace(email="budi@contoh.test", employee_id="11111111-1111-4111-8111-111111111111")
    assert await svc._printer(user) == "Budi Santoso"
    svc.repo.employee_name = AsyncMock(return_value=None)
    assert await svc._printer(SimpleNamespace(email="x@contoh.test", employee_id=None)) == "-"


def test_periodic_schedule_sheet_prints_plan_status_in_indonesian():
    day = SimpleNamespace(work_date=date(2026, 9, 14), team_name="Tim A", site_name="Pos", status="APPROVED",
                          items=1, items_done=0, items_shifted=0, avg_progress=0, titles="Instalasi 1")
    per = PeriodicReport("MEP", date(2026, 9, 14), date(2026, 9, 20), [day], [], [], "pm",
                         datetime(2026, 9, 21, tzinfo=UTC))
    ws = load_workbook(io.BytesIO(periodic_xlsx(per)))["Jadwal"]
    values = [c.value for row in ws.iter_rows() for c in row]
    assert "Disetujui" in values and "APPROVED" not in values
