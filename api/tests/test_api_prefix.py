"""
T-07 · Basis API `/api/v1` (dok 05). Web memanggil `${VITE_API_BASE_URL}/api/v1/...`, Caddy
meneruskan `/api/*` dan `/health` ke API. Hanya pemeriksaan kesehatan & dokumentasi di akar.
"""
from __future__ import annotations

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import API_PREFIX, app

ROOT_ROUTES = {"/health", "/ready"}


def test_api_prefix_matches_contract():
    assert API_PREFIX == "/api/v1"


def test_every_application_route_lives_under_api_v1():
    offenders = [
        route.path
        for route in app.routes
        if isinstance(route, APIRoute) and route.path not in ROOT_ROUTES and not route.path.startswith(API_PREFIX)
    ]

    assert offenders == []


def test_routes_answer_under_prefix_only():
    with TestClient(app) as client:
        prefixed = client.post(f"{API_PREFIX}/auth/login", json={})
        bare = client.post("/auth/login", json={})
        health = client.get("/health")

    assert prefixed.status_code == 422  # rute ada; badan permintaan kosong ditolak validasi
    assert bare.status_code == 404
    assert health.status_code == 200
