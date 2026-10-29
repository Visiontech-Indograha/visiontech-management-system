"""
A5/A6 · Validasi gambar dan header penyajian berkas.
- Gambar harus bisa didekode utuh (Pillow): PNG terpotong → 422; HEIC asli (pillow-heif) diterima; HEIC palsu → 415.
- Penyajian berkas: `X-Content-Type-Options: nosniff`; non-gambar (PDF/dokumen) selalu `attachment`.
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

import app.modules.system.controllers.files_controller as files_ctrl
from tests.conftest import World, requires_db

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (30, 120, 200)).save(buf, "PNG")
    return buf.getvalue()


def _upload(client, world: World, name: str, body: bytes, mime: str):
    return client.post("/files/upload", headers=world.headers(client, "member"),
                       files={"file": (name, body, mime)})


def test_valid_png_is_accepted(client, world: World):
    assert _upload(client, world, "ok.png", _png(), "image/png").status_code == 200


@pytest.mark.parametrize("cut", [18, "half"])
def test_truncated_png_is_rejected(client, world: World, cut):
    full = _png()
    body = full[:18] if cut == 18 else full[: len(full) // 2]
    response = _upload(client, world, "rusak.png", body, "image/png")
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "IMAGE_CORRUPT"


def test_genuine_heic_is_accepted(client, world: World):
    """HEIC asli (berkas uji 408 byte, dibuat pillow-heif) harus lolos dekode dan diterima."""
    heic = (Path(__file__).parent / "data" / "uji_valid.heic").read_bytes()
    response = _upload(client, world, "foto.heic", heic, "image/heic")
    assert response.status_code == 200, response.text


def test_fake_heic_is_rejected(client, world: World):
    fake = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 300
    response = _upload(client, world, "palsu.heic", fake, "image/heic")
    assert response.status_code == 415, response.text
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_served_file_has_nosniff_and_pdf_is_attachment(client, world: World, fake_storage, monkeypatch):
    monkeypatch.setattr(files_ctrl, "get_object_bytes", lambda key: fake_storage.get(key))
    pdf = b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\n%%EOF\n"
    uploaded = _upload(client, world, "surat.pdf", pdf, "application/pdf")
    assert uploaded.status_code == 200, uploaded.text
    file_id = uploaded.json()["file_id"]

    ticket = client.get(f"/files/{file_id}/url", headers=world.headers(client, "member"))
    assert ticket.status_code == 200, ticket.text
    served = client.get(ticket.json()["url"].replace("/api/v1", ""))
    assert served.status_code == 200, served.text
    assert served.headers["X-Content-Type-Options"] == "nosniff"
    assert served.headers["Content-Disposition"].startswith("attachment")
