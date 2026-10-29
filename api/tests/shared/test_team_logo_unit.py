"""
Uji unit tanpa DB: validasi berkas logo tim (format/ukuran/dekode/sisi), fit-contain (rasio dijaga, tak melewati
kotak), dan resolver logo (berkas hilang → default). Juga memastikan logo tim benar-benar masuk ke dokumen DOCX/PPTX.
"""
from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime

import pytest
from PIL import Image
from pptx import Presentation

from app.core import storage as storage_core
from app.core.errors import AppError
from app.modules.exports.services.builders import model as m
from app.modules.exports.services.builders.docx_builders import daily_report_docx
from app.modules.exports.services.builders.office_builders import team_week_pptx
from app.shared.documents import branding
from app.shared.documents.branding import COMPANY_BOX_PX, fit_contain_png, team_logo_or_default, validate_team_logo
from app.shared.documents.docx_kit import LOGO


def _png(size: tuple[int, int], color: tuple[int, int, int, int] = (200, 30, 30, 255)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", size, color).save(buf, "PNG")
    return buf.getvalue()


def _bbox_size(png: bytes) -> tuple[int, int]:
    """Ukuran area yang tidak transparan (isi logo, bukan kanvas kosong)."""
    alpha = Image.open(io.BytesIO(png)).convert("RGBA").getchannel("A")
    box = alpha.getbbox()
    assert box is not None
    return box[2] - box[0], box[3] - box[1]


# ── validasi berkas ──────────────────────────────────────────────────────────────────────────
def test_accepts_png_jpeg_webp_and_reports_extension():
    buf_jpg, buf_webp = io.BytesIO(), io.BytesIO()
    Image.new("RGB", (120, 80), (10, 80, 160)).save(buf_jpg, "JPEG")
    Image.new("RGB", (120, 80), (10, 80, 160)).save(buf_webp, "WEBP")
    assert validate_team_logo(_png((120, 80))) == ("image/png", "png")
    assert validate_team_logo(buf_jpg.getvalue()) == ("image/jpeg", "jpg")
    assert validate_team_logo(buf_webp.getvalue()) == ("image/webp", "webp")


def test_rejects_non_image_with_415():
    gif = io.BytesIO()
    Image.new("RGB", (100, 100)).save(gif, "GIF")
    with pytest.raises(AppError) as err:
        validate_team_logo(gif.getvalue())
    assert err.value.status == 415
    with pytest.raises(AppError) as text:
        validate_team_logo(b"bukan gambar sama sekali")
    assert text.value.status == 415


def test_rejects_truncated_png_with_422():
    truncated = _png((300, 300))[:-200]
    with pytest.raises(AppError) as err:
        validate_team_logo(truncated)
    assert err.value.status == 422


def test_rejects_file_over_two_megabytes_with_413():
    with pytest.raises(AppError) as err:
        validate_team_logo(_png((100, 100)) + b"\0" * (2 * 1024 * 1024))
    assert err.value.status == 413


@pytest.mark.parametrize("size", [(63, 200), (200, 4001)])
def test_rejects_side_outside_64_to_4000_px(size: tuple[int, int]):
    with pytest.raises(AppError) as err:
        validate_team_logo(_png(size))
    assert err.value.status == 422
    assert err.value.code == "LOGO_SIZE_INVALID"


# ── fit-contain ─────────────────────────────────────────────────────────────────────────────
def test_square_logo_is_contained_proportionally_not_stretched():
    fitted = fit_contain_png(_png((500, 500)), (300, 100))
    assert Image.open(io.BytesIO(fitted)).size == (300, 100)  # kanvas = kotak
    assert _bbox_size(fitted) == (100, 100)  # persegi tampil lebih kecil, tidak melewati tinggi kotak


def test_wide_logo_fits_width_keeping_ratio():
    fitted = fit_contain_png(_png((1000, 200)), (300, 100))
    assert Image.open(io.BytesIO(fitted)).size == (300, 100)
    assert _bbox_size(fitted) == (300, 60)  # rasio 5:1 terjaga, lebar tepat kotak


def test_fitted_logo_stays_inside_standard_box():
    for size in [(64, 4000), (4000, 64), (713, 208), (1, 1)]:
        fitted = fit_contain_png(_png(size), COMPANY_BOX_PX)
        w, h = _bbox_size(fitted)
        assert w <= COMPANY_BOX_PX[0] and h <= COMPANY_BOX_PX[1]


# ── resolver logo ───────────────────────────────────────────────────────────────────────────
def test_resolver_returns_stored_bytes_or_default(monkeypatch):
    stored = {"org/team-logo/t/f.png": b"logo-asli"}
    monkeypatch.setattr(storage_core, "get_object_bytes", lambda key: stored.get(key))
    assert team_logo_or_default("t", "org/team-logo/t/f.png") == b"logo-asli"
    assert team_logo_or_default("t", "org/team-logo/t/hilang.png") is None  # berkas hilang → default
    assert team_logo_or_default("t", None) is None  # tim tanpa logo → default


def test_resolver_survives_storage_exception(monkeypatch):
    def boom(key: str) -> bytes:
        raise ConnectionError("MinIO mati")

    monkeypatch.setattr(storage_core, "get_object_bytes", boom)
    assert team_logo_or_default("t", "k") is None


# ── dokumen memuat logo tim ─────────────────────────────────────────────────────────────────
def _docx_media(content: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        return {n: z.read(n) for n in z.namelist() if n.startswith("word/media/")}


def _daily(team_logo: bytes | None) -> m.DailyReport:
    return m.DailyReport(
        team_name="Tim Logo", division_name="Divisi Uji", work_date=m.date(2026, 10, 29), site_name="Site",
        status="APPROVED", leader_name="Ketua", points=[], roster=[], summary=None, obstacles=None,
        generated_by="-", generated_at=datetime(2026, 10, 29, tzinfo=UTC), team_logo=team_logo,
    )


def test_daily_report_docx_uses_team_logo_in_letterhead():
    custom = _png((500, 500), (20, 160, 60, 255))
    media = _docx_media(daily_report_docx(_daily(custom)))
    sizes = [Image.open(io.BytesIO(b)).size for b in media.values()]
    assert COMPANY_BOX_PX in sizes  # kop memakai kanvas logo tim (kotak standar)
    assert LOGO.read_bytes() not in media.values()  # logo default tidak dipakai


def test_daily_report_docx_falls_back_to_default_logo_without_team_logo():
    media = _docx_media(daily_report_docx(_daily(None)))
    assert LOGO.read_bytes() in media.values()


def test_team_week_pptx_uses_team_logo_on_cover_and_slides():
    report = m.TeamWeekReport(
        team_name="Tim Logo", division_name="Divisi Uji", start=m.date(2026, 10, 26), end=m.date(2026, 11, 1),
        points=[], roster=[], generated_by="-", generated_at=m.datetime(2026, 11, 1),
        team_logo=_png((1000, 200), (20, 60, 160, 255)),
    )
    prs = Presentation(io.BytesIO(team_week_pptx(report)))
    pictures = [sh for s in prs.slides for sh in s.shapes if sh.shape_type == 13]
    assert len(pictures) >= 2  # sampul + kepala slide
    assert LOGO.read_bytes() not in {sh.image.blob for sh in pictures}  # logo default tidak dipakai
    assert all(Image.open(io.BytesIO(sh.image.blob)).size == COMPANY_BOX_PX for sh in pictures)  # kanvas logo tim


def test_bast_and_surat_tugas_use_team_logo_in_letterhead():
    from datetime import date as day
    from uuid import uuid4

    from app.modules.exports.services.builders.docx_builders import bast_docx, order_sheet_docx

    order = {"completion_id": uuid4(), "order_number": "ORD-UJI-1", "client_name": "Klien uji",
             "project_title": "Proyek uji", "start_work_date": day(2026, 10, 1), "end_work_date": day(2026, 10, 2),
             "bom_items": [], "summary_notes": None, "obstacles": None}
    report = m.CompletionReport(
        order=order, points=[], roster=[], bom=[], generated_by="-", generated_at=m.datetime(2026, 10, 2),
        team_logo=_png((400, 400), (160, 20, 20, 255)),
    )
    for content in (bast_docx(report), order_sheet_docx(report)):
        assert COMPANY_BOX_PX in [Image.open(io.BytesIO(b)).size for b in _docx_media(content).values()]
        assert LOGO.read_bytes() not in _docx_media(content).values()


async def test_survey_letterhead_company_logo_is_replaced_by_team_logo(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    from app.modules.exports.services import export_service as es

    repo = MagicMock()
    repo.team_logo_keys = AsyncMock(return_value={"t1": "key-tim"})
    monkeypatch.setattr(branding, "custom_logos", lambda org: {"company": b"org", "client": b"klien"})
    monkeypatch.setattr(storage_core, "get_object_bytes", lambda key: b"tim" if key == "key-tim" else None)
    svc = es.ExportService(repo, MagicMock())
    user = SimpleNamespace(organization_id="o")

    assert await svc._survey_logos_for({"team_id": "t1"}, user) == {"company": b"tim", "client": b"klien"}
    repo.team_logo_keys = AsyncMock(return_value={})  # tim tanpa logo: logo organisasi tetap dipakai
    assert await svc._survey_logos_for({"team_id": "t1"}, user) == {"company": b"org", "client": b"klien"}
