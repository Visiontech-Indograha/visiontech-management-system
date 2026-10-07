"""
T-09 · Uji asap SELURUH rute (P-4). Rute diinventaris otomatis dari `app.routes`, jadi rute baru
langsung ikut teruji — tidak ada rute yang lolos tanpa pemeriksaan:
1. Tanpa token → 401 (kecuali rute publik yang didaftarkan eksplisit di bawah).
2. Dengan token ADMIN, parameter jalur acak, badan kosong → tidak pernah 500.
Uji perilaku per endpoint (tulis lalu baca ulang) tetap wajib di berkas uji masing-masing.
"""
from __future__ import annotations

import re
import uuid

import pytest

from app.main import API_PREFIX
from tests.conftest import login_headers, requires_db
from tests.route_inventory import all_routes

# Rute yang sengaja dapat dipanggil tanpa login. Menambah baris di sini = keputusan keamanan.
PUBLIC_ROUTES = {
    ("POST", "/auth/login"),
    ("POST", "/auth/refresh"),
    ("POST", "/auth/logout"),
    ("GET", "/verify/{token}"),   # fase 6: verifikasi QR publik, dibatasi 30/menit per IP
}

ROUTES = [(method, path.removeprefix(API_PREFIX)) for method, path in all_routes() if path.startswith(API_PREFIX)]


def _concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", lambda _: str(uuid.uuid4()), path)


def test_inventory_is_not_empty():
    assert len(ROUTES) > 20


def test_public_routes_exist():
    assert set(ROUTES) >= PUBLIC_ROUTES


@requires_db
@pytest.mark.parametrize(("method", "path"), [r for r in ROUTES if r not in PUBLIC_ROUTES])
def test_route_requires_login(client, method: str, path: str):
    response = client.request(method, _concrete(path), json={})

    assert response.status_code == 401, f"{method} {path} → {response.status_code}: {response.text[:200]}"


@requires_db
@pytest.mark.parametrize(("method", "path"), ROUTES)
def test_route_never_crashes_for_admin(client, make_user, method: str, path: str):
    headers = login_headers(client, make_user("ADMIN"))

    response = client.request(method, _concrete(path), json={}, headers=headers)

    assert response.status_code < 500, f"{method} {path} → {response.status_code}: {response.text[:300]}"


def test_openapi_schema_builds():
    """Web membangkitkan tipe dari skema ini (`npm run gen:api`, dok 05/11); /docs juga bergantung padanya."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert f"{API_PREFIX}/auth/login" in response.json()["paths"]
