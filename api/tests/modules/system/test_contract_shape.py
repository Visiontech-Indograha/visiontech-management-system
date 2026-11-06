"""Penjaga bentuk respons beku: dipakai aplikasi lama yang sudah terpasang (versi & pembaruan otomatis)."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.version import APP_VERSION
from app.main import app
from app.modules.system.dependencies import get_app_release_service
from app.modules.system.services.app_release_service import AppReleaseService

# Kunci dan tipe JSON yang dipakai APK lama: tidak boleh hilang, ganti nama, atau berubah tipe.
FROZEN_UPDATE_KEYS: dict[str, tuple[type, ...]] = {
    "status": (str,),
    "current_build": (int,),
    "latest_build": (int, type(None)),
    "latest_version": (str, type(None)),
    "min_build": (int, type(None)),
    "released_at": (str, type(None)),
    "notes": (list,),
    "download": (dict, type(None)),
}
FROZEN_DOWNLOAD_KEYS: dict[str, type] = {"abi": str, "url": str, "sha256": str, "size": int}


def test_version_shape_is_exact():
    response = TestClient(app).get("/api/v1/version")
    assert response.status_code == 200
    assert response.json() == {"version": APP_VERSION}


def test_android_update_shape_is_frozen_without_release(tmp_path: Path):
    app.dependency_overrides[get_app_release_service] = lambda: AppReleaseService(str(tmp_path))
    try:
        response = TestClient(app).get("/api/v1/app/android/update", params={"build": 1})
    finally:
        app.dependency_overrides.pop(get_app_release_service, None)
    assert response.status_code == 200, response.text
    body = response.json()
    for key, types in FROZEN_UPDATE_KEYS.items():
        assert key in body, f"kunci {key} hilang dari /app/android/update"
        assert isinstance(body[key], types), f"tipe {key} berubah"
    assert body["status"] == "UP_TO_DATE"
