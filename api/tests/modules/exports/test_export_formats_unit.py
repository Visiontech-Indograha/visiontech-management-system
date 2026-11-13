"""
api/tests/modules/exports/test_export_formats_unit.py
Uji unit (tanpa DB): isi setara antar format, catatan foto terpotong, istilah Bahasa Indonesia awam di dokumen,
validasi skema (format, Senin, 7 hari), dan konversi PDF lewat satu sumber (Word).
"""
from __future__ import annotations

import io
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import docx
import pytest
from openpyxl import load_workbook
from pptx import Presentation
from pydantic import ValidationError as PydanticError

from app.core.errors import AppError
from app.modules.exports.schemas.export_schema import CompletionExportRequest, TeamWeekExportRequest
from app.modules.exports.services import export_service as es
from app.modules.exports.services.builders.docx_builders import (
    bast_docx,
    daily_report_docx,
    order_sheet_docx,
    progress_docx,
    survey_report_docx,
    team_week_docx,
)
from app.modules.exports.services.builders.model import DailyReport, omitted_note
from app.modules.exports.services.builders.office_builders import (
    bast_pptx,
    completion_xlsx,
    daily_report_pptx,
    order_sheet_pptx,
    periodic_xlsx,
    survey_pptx,
    survey_report_pptx,
    team_week_pptx,
)
from app.modules.exports.services.builders.survey_template import build_survey_docx
from tests.modules.exports.test_export_unit import _report as completion_report
from tests.modules.exports.test_survey_template import _doc as survey_doc
from tests.modules.exports.test_team_week_unit import _report as week_report

FORBIDDEN_TERMS = ("Bill of", "BoQ", "BoM", "BAST", "Survey Report", "SURVEY REPORT", "Assessment")


def docx_text(content: bytes) -> str:
    d = docx.Document(io.BytesIO(content))
    cells = [c.text for t in d.tables for r in t.rows for c in r.cells]
    parts = [p.text for p in d.paragraphs] + cells
    for section in d.sections:
        parts += [p.text for p in section.header.paragraphs] + [p.text for p in section.footer.paragraphs]
    return "\n".join(parts)


def pptx_text(content: bytes) -> str:
    parts: list[str] = []
    for slide in Presentation(io.BytesIO(content)).slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                parts.append(shape.text_frame.text)
            if shape.has_table:
                parts.extend(c.text for r in shape.table.rows for c in r.cells)
    return "\n".join(parts)


def daily_report() -> DailyReport:
    w = week_report()
    return DailyReport(team_name=w.team_name, division_name=w.division_name, work_date=date(2026, 10, 27),
                       site_name="Kantor Rumbai", status="APPROVED", leader_name="Zulkifli", points=w.points,
                       roster=w.roster, summary="Semua titik aman.", obstacles="Hujan deras.",
                       generated_by="ketua", generated_at=w.generated_at)


# ── Isi setara antar format ──────────────────────────────────────────────────
def test_team_week_word_and_slides_carry_the_same_facts():
    report = week_report()
    word, slides = docx_text(team_week_docx(report)), pptx_text(team_week_pptx(report))
    for fact in ("Tim CCTV", "Divisi CCTV", "Zulkifli", "Survei titik", "Pasang kamera", "26 Oktober 2026",
                 "1 November 2026", "Diuji normal."):
        assert fact in word, ("Word", fact)
        assert fact in slides, ("PPTX", fact)


def test_daily_report_word_and_slides_carry_the_same_facts():
    report = daily_report()
    word, slides = docx_text(daily_report_docx(report)), pptx_text(daily_report_pptx(report))
    for fact in ("Tim CCTV", "Divisi CCTV", "Zulkifli", "Survei titik", "Pasang kamera", "27 Oktober 2026",
                 "Semua titik aman.", "Hujan deras.", "Kantor Rumbai"):
        assert fact in word, ("Word", fact)
        assert fact in slides, ("PPTX", fact)


def test_order_documents_word_and_slides_carry_the_same_facts():
    report = completion_report()
    pairs = [(bast_docx, bast_pptx), (order_sheet_docx, order_sheet_pptx), (progress_docx, es.completion_pptx)]
    for word_builder, slide_builder in pairs:
        word, slides = docx_text(word_builder(report)), pptx_text(slide_builder(report))
        for fact in (report.points[0].title, report.points[-1].title):
            assert fact in word and fact in slides, (word_builder.__name__, fact)
    survey_titles = [p.title for p in report.survey_points]
    assert survey_titles
    assert all(t in docx_text(survey_report_docx(report)) and t in pptx_text(survey_report_pptx(report))
               for t in survey_titles)


def test_survey_slides_carry_the_survey_facts():
    doc = survey_doc("CCTV")
    slides = pptx_text(survey_pptx(doc))
    assert doc.client in slides and doc.location in slides and doc.date_text in slides
    assert all(p.name in slides for p in doc.points)
    assert "Laporan Survei" in slides


# ── Foto terpotong dicatat ───────────────────────────────────────────────────
def test_omitted_note_text():
    assert omitted_note(0) is None
    assert omitted_note(7) == "Catatan: 7 foto lain tidak disertakan dalam dokumen ini."


@pytest.mark.parametrize("count", [3, 41])
def test_every_builder_writes_the_omitted_photo_note(count: int):
    note = f"{count} foto lain tidak disertakan"
    c = completion_report()
    c.omitted_photos = count
    w = week_report()
    w.omitted_photos = count
    d = daily_report()
    d.omitted_photos = count
    s = survey_doc("ACS")
    s.omitted_photos = count
    s2 = survey_doc("CCTV")
    s2.omitted_photos = count
    texts = [docx_text(bast_docx(c)), docx_text(survey_report_docx(c)), docx_text(progress_docx(c)),
             pptx_text(es.completion_pptx(c)), docx_text(team_week_docx(w)), pptx_text(team_week_pptx(w)),
             docx_text(daily_report_docx(d)), pptx_text(daily_report_pptx(d)),
             docx_text(build_survey_docx(s)), docx_text(build_survey_docx(s2)), pptx_text(survey_pptx(s))]
    for text in texts:
        assert note in text


def test_no_note_when_nothing_is_omitted():
    assert "tidak disertakan" not in docx_text(team_week_docx(week_report()))
    assert "tidak disertakan" not in pptx_text(team_week_pptx(week_report()))


@pytest.mark.anyio
async def test_points_counts_photos_cut_by_the_limits():
    def item(i: int, photos: int) -> SimpleNamespace:
        refs = [{"file_id": f"00000000-0000-4000-8000-{i:08d}{n:04d}", "requirement_id": None} for n in range(photos)]
        import json
        return SimpleNamespace(item_id=f"i{i}", photos=json.dumps(refs), title=f"T{i}", task_phase="SURVEY",
                               status="DONE", work_date=date(2026, 10, 26), team_name="t", location_name="",
                               site_name="", site_lat=None, site_lng=None, target_qty=1, completed_qty=1,
                               progress_percent=100, notes=None, delay_reason=None, assignees="", work_type_name="")

    svc = es.ExportService.__new__(es.ExportService)
    repo = MagicMock()
    repo.image_keys = AsyncMock(return_value={})
    repo.requirement_names = AsyncMock(return_value={})
    svc.repo = repo
    # 3 item x 6 foto = 18 diterima per item (10 foto x 3 = 30 foto di sumber; 4 foto per item terpotong batas 6)
    items = [item(1, 10), item(2, 10), item(3, 10)]
    await svc._points(items, [], [], 10)
    # per item 10 -> 6 (4 terpotong x 3 = 12), lalu 18 id unik -> batas 10 (8 terpotong)
    assert svc._omitted_photos == 12 + 8


# ── Istilah Indonesia awam ───────────────────────────────────────────────────
def test_documents_use_plain_indonesian_terms():
    report = completion_report()
    texts = [docx_text(bast_docx(report)), docx_text(order_sheet_docx(report)),
             docx_text(survey_report_docx(report)), docx_text(progress_docx(report)),
             pptx_text(es.completion_pptx(report)), pptx_text(bast_pptx(report)),
             docx_text(build_survey_docx(survey_doc("ACS"))), docx_text(build_survey_docx(survey_doc("CCTV"))),
             pptx_text(survey_pptx(survey_doc("CCTV")))]
    for text in texts:
        for term in FORBIDDEN_TERMS:
            assert term.lower() not in text.lower(), term
    assert "berita acara serah terima" in texts[0].lower()
    assert "laporan survei" in texts[2].lower()
    assert "Rincian Volume dan Biaya" in texts[2]
    assert "Rincian Volume dan Biaya" in docx_text(build_survey_docx(survey_doc("CCTV")))
    assert "Rincian Volume dan Biaya" in docx_text(build_survey_docx(survey_doc("ACS")))


def test_spreadsheets_use_plain_indonesian_terms():
    wb = load_workbook(io.BytesIO(completion_xlsx(completion_report())))
    assert "Rincian Volume dan Biaya" in wb.sheetnames
    assert wb["Rincian Volume dan Biaya"]["A1"].value == "Rincian Volume dan Biaya"
    for ws in wb:
        for row in ws.iter_rows(values_only=True):
            for cell in row:
                assert not any(t.lower() in str(cell).lower() for t in ("BoQ", "Bill of", "BoM")), cell
    assert periodic_xlsx is not None


# ── Skema ────────────────────────────────────────────────────────────────────
def test_schema_validates_format_monday_and_seven_days():
    team = "00000000-0000-4000-8000-000000000001"
    assert CompletionExportRequest(template="BAST").export_format is None
    assert CompletionExportRequest(template="BAST", export_format="PDF").export_format == "PDF"
    with pytest.raises(PydanticError):
        CompletionExportRequest(template="BAST", export_format="DOC")  # type: ignore[arg-type]
    ok = TeamWeekExportRequest(team_id=team, start_date=date(2026, 10, 26))  # type: ignore[arg-type]
    assert ok.export_format is None
    with pytest.raises(PydanticError, match="Senin"):
        TeamWeekExportRequest(team_id=team, start_date=date(2026, 10, 27))  # type: ignore[arg-type]
    with pytest.raises(PydanticError, match="7 hari"):
        TeamWeekExportRequest(team_id=team, start_date=date(2026, 10, 26),  # type: ignore[arg-type]
                              end_date=date(2026, 11, 8))
    TeamWeekExportRequest(team_id=team, start_date=date(2026, 10, 26),  # type: ignore[arg-type]
                          end_date=date(2026, 11, 1))


# ── PDF = Word yang dikonversi (satu sumber) ─────────────────────────────────
@pytest.mark.anyio
async def test_pdf_is_the_converted_word_and_fails_clearly_without_converter(monkeypatch: pytest.MonkeyPatch):
    seen: list[bytes] = []

    async def convert(content: bytes) -> bytes:
        seen.append(content)
        return b"%PDF-1"

    monkeypatch.setattr(es, "docx_to_pdf", convert)
    word = lambda data: b"WORD:" + data  # noqa: E731
    slides = lambda data: b"SLIDES:" + data  # noqa: E731
    assert await es._render("PDF", word, slides, b"x") == b"%PDF-1" and seen == [b"WORD:x"]
    assert await es._render("WORD_DOCX", word, slides, b"x") == b"WORD:x"
    assert await es._render("PPTX", word, slides, b"x") == b"SLIDES:x"

    async def none(content: bytes) -> None:
        return None

    monkeypatch.setattr(es, "docx_to_pdf", none)
    with pytest.raises(AppError) as err:
        await es._render("PDF", word, slides, b"x")
    assert err.value.status == 503 and err.value.code == "PDF_UNAVAILABLE"
