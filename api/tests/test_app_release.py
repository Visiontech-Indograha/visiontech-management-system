"""
Pembaruan otomatis aplikasi Android (docs/32, keputusan pemilik 2026-10-07).
- GET /app/android/update: UP_TO_DATE | OPTIONAL | REQUIRED dari `APP_RELEASE_DIR/android/latest.json` (tanpa DB).
- GET|HEAD /app/android/files/{name}: hanya nama yang tercantum di manifest; GET /app/android/latest.apk → 302.
Prinsip yang dijaga: manifest hilang/rusak tidak pernah mengunci HP; REQUIRED hanya bila ada berkas untuk ABI HP.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_app_release_service
from app.main import app
from app.services.app_release_service import AppReleaseService

APK = b"PK\x03\x04 bukan apk sungguhan" * 64
BASE = "/api/v1/app/android"


def _write(root: Path, **override: object) -> dict[str, object]:
    d = root / "android"
    d.mkdir(parents=True, exist_ok=True)
    files = [
        ("arm64-v8a", "vms-1.2.0-6-arm64-v8a.apk"),
        ("armeabi-v7a", "vms-1.2.0-6-armeabi-v7a.apk"),
    ]
    entries = []
    for abi, name in files:
        (d / name).write_bytes(APK)
        entries.append({"abi": abi, "name": name, "sha256": hashlib.sha256(APK).hexdigest(), "size": len(APK)})
    manifest: dict[str, object] = {
        "version_name": "1.2.0", "build": 6, "min_build": 4, "released_at": "2026-10-07T21:00:00+07:00",
        "notes": ["Perbaikan absensi"], "files": entries,
    }
    manifest.update(override)
    path = d / "latest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    stamp = time.time() + len(json.dumps(manifest))   # mtime berbeda tiap tulis agar cache dibaca ulang
    os.utime(path, (stamp, stamp))
    return manifest


@pytest.fixture
def release(tmp_path: Path):
    app.dependency_overrides[get_app_release_service] = lambda: AppReleaseService(str(tmp_path))
    yield tmp_path
    app.dependency_overrides.pop(get_app_release_service, None)


@pytest.fixture
def api() -> TestClient:
    return TestClient(app)


def _update(api: TestClient, build: int, *abis: str) -> dict:
    response = api.get(f"{BASE}/update", params={"build": build, "abi": list(abis)})
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()


def test_no_release_dir_or_manifest_is_always_up_to_date(api, release):
    assert _update(api, 1, "arm64-v8a")["status"] == "UP_TO_DATE"
    no_dir = AppReleaseService("")
    assert no_dir.check_update(1, ["arm64-v8a"]).status == "UP_TO_DATE"


def test_status_follows_build_and_min_build(api, release):
    _write(release)
    assert _update(api, 6, "arm64-v8a")["status"] == "UP_TO_DATE"
    optional = _update(api, 5, "arm64-v8a")
    assert optional["status"] == "OPTIONAL"
    assert optional["download"] == {
        "abi": "arm64-v8a", "url": f"{BASE}/files/vms-1.2.0-6-arm64-v8a.apk",
        "sha256": hashlib.sha256(APK).hexdigest(), "size": len(APK),
    }
    assert optional["latest_version"] == "1.2.0" and optional["notes"] == ["Perbaikan absensi"]
    assert _update(api, 3, "arm64-v8a")["status"] == "REQUIRED"


def test_file_follows_device_abi_order_and_never_requires_without_a_file(api, release):
    _write(release)
    assert _update(api, 3, "armeabi-v7a", "arm64-v8a")["download"]["abi"] == "armeabi-v7a"
    no_file = _update(api, 3, "x86_64")
    assert no_file["status"] == "UP_TO_DATE" and no_file["download"] is None   # tidak mengunci HP tanpa unduhan


def test_min_build_cannot_exceed_latest_build(api, release):
    _write(release, min_build=99)
    out = _update(api, 5, "arm64-v8a")
    assert out["min_build"] == 6 and out["status"] == "REQUIRED"


def test_broken_manifest_is_treated_as_no_release(api, release):
    _write(release)
    (release / "android" / "latest.json").write_text("{rusak", encoding="utf-8")
    os.utime(release / "android" / "latest.json", (time.time() + 99, time.time() + 99))
    assert _update(api, 1, "arm64-v8a")["status"] == "UP_TO_DATE"


def test_download_serves_only_manifest_files(api, release):
    _write(release)
    ok = api.get(f"{BASE}/files/vms-1.2.0-6-arm64-v8a.apk")
    assert ok.status_code == 200 and ok.content == APK
    assert ok.headers["content-type"] == "application/vnd.android.package-archive"
    assert "immutable" in ok.headers["cache-control"]
    head = api.head(f"{BASE}/files/vms-1.2.0-6-arm64-v8a.apk")
    assert head.status_code == 200 and head.headers["content-length"] == str(len(APK))
    (release / "android" / "rahasia.apk").write_bytes(b"x")
    for name in ("latest.json", "rahasia.apk", "..%2Flatest.json", "lain.apk"):
        assert api.get(f"{BASE}/files/{name}").status_code == 404, name


def test_latest_apk_redirects_to_current_file(api, release):
    assert api.get(f"{BASE}/latest.apk", follow_redirects=False).status_code == 404     # belum ada rilis
    _write(release)
    r = api.get(f"{BASE}/latest.apk", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == f"{BASE}/files/vms-1.2.0-6-arm64-v8a.apk"
    v7 = api.get(f"{BASE}/latest.apk", params={"abi": "armeabi-v7a"}, follow_redirects=False)
    assert v7.headers["location"].endswith("armeabi-v7a.apk")


def test_routes_are_public(api, release):
    _write(release)
    assert api.get(f"{BASE}/update", params={"build": 1}).status_code == 200      # tanpa token
