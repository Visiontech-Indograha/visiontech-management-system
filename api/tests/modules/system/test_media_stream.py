"""
Media rujukan publik (/media/preview, /media/download): hanya folder rujukan di api/uploads (sop, tools, vehicles)
dan jenis gambar/PDF. Dulu rute ini membaca berkas apa pun di folder api/ tanpa login (mis. `.env`) dan
/media/upload menulis ke disk tanpa login.
"""
from __future__ import annotations

import pytest

from app.modules.system.routes.media_stream_route import _resolve_file_path


@pytest.mark.parametrize("path", [
    ".env", "/uploads/../.env", "sop/../../.env", "app/main.py", "employees/download_038.jpg",
    "docs/kontrak.pdf", "sop/script.py", "/api/v1/media/preview?path=.env", "C:/Windows/win.ini",
])
def test_paths_outside_public_reference_folders_are_refused(path: str):
    assert _resolve_file_path(path) is None


def test_secret_file_is_not_served(client):
    response = client.get("/media/download", params={"path": ".env"})
    assert response.status_code == 404
    assert b"DATABASE_URL" not in response.content


def test_upload_route_is_gone(client):
    assert client.post("/media/upload", files={"file": ("x.txt", b"x", "text/plain")}).status_code in (404, 405)
