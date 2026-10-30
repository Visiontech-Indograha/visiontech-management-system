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
        assert branding.team_logo_or_default("tim-1", "tenant/team-logo/tim-1/a.png") is None
        assert branding.team_logo_or_default("tim-1", "tenant/team-logo/tim-1/a.png") is None
        assert branding.team_logo_or_default("tim-2", "tenant/team-logo/tim-2/b.png") is None
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "logo" in warnings[0].getMessage().lower()


def test_storage_exception_warns_once_and_returns_none(monkeypatch, caplog):
    def boom(key):
        raise ConnectionError("minio down")

    monkeypatch.setattr(storage_core, "get_object_bytes", boom)
    with caplog.at_level(logging.WARNING, logger=branding.__name__):
        assert branding.team_logo_or_default("tim-1", "k.png") is None
        assert branding.team_logo_or_default("tim-1", "k.png") is None
    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1


def test_no_storage_key_is_not_a_failure(monkeypatch, caplog):
    monkeypatch.setattr(storage_core, "get_object_bytes", lambda key: pytest.fail("tidak boleh diakses"))
    with caplog.at_level(logging.WARNING, logger=branding.__name__):
        assert branding.team_logo_or_default("tim-1", None) is None
    assert not [r for r in caplog.records if r.levelno == logging.WARNING]


def test_bast_letterhead_keeps_bundled_logo_when_storage_fails(monkeypatch):
    monkeypatch.setattr(storage_core, "get_object_bytes", lambda key: None)
    team_logo = branding.team_logo_or_default("tim-1", "k.png")
    doc = docx_kit.new_document()
    docx_kit.letterhead(doc, "PT VISIONTECH INDOGRAHA", "Berita Acara Serah Terima Pekerjaan",
                        "Nomor: UJI3-PO-001", "PT UJI3 Klien Pengujian", team_logo=team_logo)
    reopened = Document(io.BytesIO(docx_kit.to_bytes(doc)))
    blobs = [part.blob for part in reopened.part.package.iter_parts() if part.partname.startswith("/word/media/")]
    assert LOGO.read_bytes() in blobs  # logo bawaan repo tetap terpasang di kop
    assert reopened.inline_shapes, "kop tanpa gambar logo"
