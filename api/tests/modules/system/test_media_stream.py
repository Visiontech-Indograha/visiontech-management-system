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


@pytest.mark.parametrize("path", [
    "/uploads/employees/Ade_Candra_3x4_Red.jpg", "/uploads/inspections/x.jpg", "/uploads/docs/x.pdf",
    "/uploads/sop/x.png", "/uploads/", "/uploads/../.env",
])
def test_uploads_folder_is_not_mounted_as_static_files(client, path: str):
    """Folder `uploads/` tidak boleh disajikan statis tanpa login (foto karyawan, inspeksi, dokumen)."""
    assert client.get(path).status_code in (404, 405)
