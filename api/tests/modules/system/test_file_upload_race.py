"""
P9-1 · Temuan uji beban: dua unggahan bersamaan berisi berkas yang sama (SHA-256 sama, mis. tombol tertekan dua kali)
dulu berakhir 500 — pemeriksaan duplikat lolos di keduanya, lalu INSERT kedua melanggar unik (organisasi, sha256).
Kini INSERT memakai ON CONFLICT: permintaan kedua memakai berkas yang sudah tercatat.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from app.modules.system.services.file_service import FileService
from tests.conftest import World, requires_db, sync_query

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (24, 24), (12, 34, 56)).save(buf, "PNG")
    return buf.getvalue()


def test_upload_that_loses_the_dedup_race_reuses_the_existing_file(client, world: World, monkeypatch):
    body = _png()
    first = client.post("/files/upload", headers=world.headers(client, "member"),
                        files={"file": ("a.png", body, "image/png")})
    assert first.status_code == 200, first.text

    async def missed(self, org_id, user_id, keys):   # jendela balapan: pemeriksaan duplikat belum melihat baris pertama
        return None

    monkeypatch.setattr(FileService, "duplicate_of", missed)
    second = client.post("/files/upload", headers=world.headers(client, "member"),
                         files={"file": ("b.png", body, "image/png")})

    assert second.status_code == 200, second.text
    assert second.json()["file_id"] == first.json()["file_id"]
    assert sync_query("SELECT count(*) FROM file_object WHERE office_id = %s", (world.org_id,))[0][0] == 1
