"""
A4 · Deduplikasi unggahan hanya di antara berkas milik pengunggah yang sama. Pengguna lain yang mengunggah isi
identik mendapat berkas sendiri (id berbeda); keberadaan berkas pengguna lain tidak bocor.
"""
from __future__ import annotations

import io

from PIL import Image

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), (200, 10, 90)).save(buf, "PNG")
    return buf.getvalue()


def _upload(client, world: World, who: str, body: bytes):
    response = client.post("/files/upload", headers=world.headers(client, who),
                           files={"file": ("foto.png", body, "image/png")})
    assert response.status_code == 200, response.text
    return response.json()


def test_identical_upload_by_other_user_is_not_deduplicated_against_theirs(client, world: World, fake_storage):
    body = _png()
    pm_first = _upload(client, world, "pm", body)["file_id"]
    member_first = _upload(client, world, "member", body)
    assert member_first["file_id"] != pm_first
    assert member_first["message"] == "Berkas berhasil diunggah."

    assert _upload(client, world, "member", body)["file_id"] == member_first["file_id"]
    assert _upload(client, world, "pm", body)["file_id"] == pm_first
    rows = sync_query("SELECT count(*) FROM file_object WHERE office_id = %s", (world.org_id,))[0][0]
    assert rows == 2
