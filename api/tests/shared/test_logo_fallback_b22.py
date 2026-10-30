"""B22: logo kop selalu terpasang. Storage (MinIO) gagal → logo bawaan repo yang dipakai (bukan kosong), dan
kegagalan mengambil logo tim tercatat sebagai WARNING sekali (bukan senyap, bukan berulang per dokumen)."""
from __future__ import annotations

import io
import logging

import pytest
from docx import Document

from app.core import storage as storage_core
from app.shared.documents import branding, docx_kit
from app.shared.documents.docx_kit import LOGO


@pytest.fixture(autouse=True)
def _reset_warn_flag(monkeypatch):
    monkeypatch.setattr(branding, "_logo_warned", False, raising=False)


def test_storage_failure_warns_once_and_returns_none(monkeypatch, caplog):
    monkeypatch.setattr(storage_core, "get_object_bytes", lambda key: None)  # MinIO mati → None
    with caplog.at_level(logging.WARNING, logger=branding.__name__):
        assert branding.team_logo_bytes("tim-1", "tenant/team-logo/tim-1/a.png") is None
        assert branding.team_logo_bytes("tim-1", "tenant/team-logo/tim-1/a.png") is None
        assert branding.team_logo_bytes("tim-2", "tenant/team-logo/tim-2/b.png") is None
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "logo" in warnings[0].getMessage().lower()


def test_storage_exception_warns_once_and_returns_none(monkeypatch, caplog):
    def boom(key):
        raise ConnectionError("minio down")

    monkeypatch.setattr(storage_core, "get_object_bytes", boom)
    with caplog.at_level(logging.WARNING, logger=branding.__name__):
        assert branding.team_logo_bytes("tim-1", "k.png") is None
        assert branding.team_logo_bytes("tim-1", "k.png") is None
    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1


def test_no_storage_key_is_not_a_failure(monkeypatch, caplog):
    monkeypatch.setattr(storage_core, "get_object_bytes", lambda key: pytest.fail("tidak boleh diakses"))
    with caplog.at_level(logging.WARNING, logger=branding.__name__):
        assert branding.team_logo_bytes("tim-1", None) is None
    assert not [r for r in caplog.records if r.levelno == logging.WARNING]


def test_bast_letterhead_keeps_bundled_logo_when_storage_fails(monkeypatch):
    monkeypatch.setattr(storage_core, "get_object_bytes", lambda key: None)
    doc = docx_kit.new_document()
    docx_kit.letterhead(doc, "PT VISIONTECH INDOGRAHA", "Berita Acara Serah Terima Pekerjaan",
                        "Nomor: UJI3-PO-001", "PT UJI3 Klien Pengujian", logos=branding.kop_logos("tim-1", "k.png"))
    reopened = Document(io.BytesIO(docx_kit.to_bytes(doc)))
    assert len(reopened.inline_shapes) == 1  # logo Visiontech bawaan tetap terpasang di kop



def _png(size: tuple[int, int] = (300, 80)) -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGBA", size, (200, 30, 30, 255)).save(out, "PNG")
    return out.getvalue()


def test_kop_logos_always_include_visiontech_and_team_logo(monkeypatch):
    team_png = _png()
    monkeypatch.setattr(storage_core, "get_object_bytes", lambda key: team_png if key == "k.png" else None)
    assert branding.kop_logos("tim-1", "k.png") == (LOGO.read_bytes(), team_png)
    assert branding.kop_logos("tim-1", None) == (LOGO.read_bytes(), None)  # tim tanpa logo: Visiontech saja


def test_kop_logos_keep_visiontech_when_storage_is_down(monkeypatch):
    monkeypatch.setattr(storage_core, "get_object_bytes", lambda key: None)
    assert branding.kop_logos("tim-1", "k.png") == (LOGO.read_bytes(), None)


def test_letterhead_shows_visiontech_and_team_logo_side_by_side(monkeypatch):
    monkeypatch.setattr(storage_core, "get_object_bytes", lambda key: _png())
    doc = docx_kit.new_document()
    docx_kit.letterhead(doc, "PT VISIONTECH INDOGRAHA", "Laporan Harian Tim", "Senin",
                        None, logos=branding.kop_logos("tim-1", "k.png"))
    reopened = Document(io.BytesIO(docx_kit.to_bytes(doc)))
    assert len(reopened.inline_shapes) == 2  # logo Visiontech + logo tim
    widths = {round(s.width.cm, 2) for s in reopened.inline_shapes}
    heights = {round(s.height.cm, 2) for s in reopened.inline_shapes}
    assert len(widths) == 1 and len(heights) == 1  # format & proporsi seragam


def test_letterhead_without_team_logo_still_shows_visiontech(monkeypatch):
    monkeypatch.setattr(storage_core, "get_object_bytes", lambda key: None)
    doc = docx_kit.new_document()
    docx_kit.letterhead(doc, "PT VISIONTECH INDOGRAHA", "Laporan Harian Tim", None, None,
                        logos=branding.kop_logos("tim-1", None))
    reopened = Document(io.BytesIO(docx_kit.to_bytes(doc)))
    assert len(reopened.inline_shapes) == 1
