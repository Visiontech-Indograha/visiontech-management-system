"""
Rate limit token bucket (F-19): unit tanpa basis data.

Mencakup: bucket habis -> 429 + Retry-After saat RATE_LIMIT_ENFORCE=true; saat false hanya log WARNING;
pembacaan IP klien hanya dari proxy tepercaya; rute yang dilindungi memang memakai dependency ini.
"""

from __future__ import annotations

import logging

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

import app.core.rate_limit as rl
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.rate_limit import (
    GROUP_AUTH,
    TokenBucketLimiter,
    client_ip,
    rate_limit,
    set_limiter,
)


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _request(peer: str, xff: str | None = None, authorization: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if xff is not None:
        headers.append((b"x-forwarded-for", xff.encode()))
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": headers,
            "client": (peer, 40000),
        }
    )


# ---------- token bucket ----------


def test_bucket_habis_lalu_isi_ulang_sesuai_waktu() -> None:
    clock = _Clock()
    limiter = TokenBucketLimiter({GROUP_AUTH: 2}, clock=clock)  # 2 per menit = 1 token per 30 detik

    assert limiter.hit(GROUP_AUTH, "ip:a") == 0
    assert limiter.hit(GROUP_AUTH, "ip:a") == 0
    assert limiter.hit(GROUP_AUTH, "ip:a") == 30  # habis: tunggu 30 detik untuk satu token

    clock.now += 29
    assert limiter.hit(GROUP_AUTH, "ip:a") == 1  # belum cukup waktu
    clock.now += 1
    assert limiter.hit(GROUP_AUTH, "ip:a") == 0  # tepat 30 detik kemudian: satu token kembali


def test_kunci_berbeda_punya_bucket_sendiri() -> None:
    limiter = TokenBucketLimiter({GROUP_AUTH: 1}, clock=_Clock())
    assert limiter.hit(GROUP_AUTH, "ip:a") == 0
    assert limiter.hit(GROUP_AUTH, "ip:a") > 0
    assert limiter.hit(GROUP_AUTH, "ip:b") == 0


def test_batas_memori_membuang_bucket_terlama() -> None:
    limiter = TokenBucketLimiter({GROUP_AUTH: 1}, clock=_Clock(), max_buckets=5)
    for i in range(50):
        limiter.hit(GROUP_AUTH, f"ip:{i}")
    assert len(limiter._buckets) <= 5


def test_limit_nol_ditolak() -> None:
    with pytest.raises(ValueError):
        TokenBucketLimiter({GROUP_AUTH: 0})


# ---------- IP klien ----------


@pytest.fixture
def trusted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", "10.0.0.0/8, 192.168.1.5")


def test_xff_diabaikan_bila_tanpa_proxy_tepercaya(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", "")
    assert client_ip(_request("198.51.100.9", xff="203.0.113.7")) == "198.51.100.9"


def test_xff_dibaca_dari_proxy_tepercaya(trusted: None) -> None:
    # Hop dibaca dari kanan: 10.0.0.9 adalah proxy tepercaya, 203.0.113.7 adalah klien.
    req = _request("10.0.0.5", xff="203.0.113.7, 10.0.0.9")
    assert client_ip(req) == "203.0.113.7"


def test_xff_dari_peer_tidak_tepercaya_diabaikan(trusted: None) -> None:
    assert client_ip(_request("198.51.100.9", xff="203.0.113.7")) == "198.51.100.9"


def test_xff_rusak_kembali_ke_peer(trusted: None) -> None:
    assert client_ip(_request("192.168.1.5", xff="bukan-ip")) == "192.168.1.5"


def test_xff_rantai_docker_gateway_dan_klien(monkeypatch: pytest.MonkeyPatch) -> None:
    # Peer = kontainer web (172.20.0.5); XFF dari Caddy: klien tailnet, lalu gateway Docker.
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", "172.20.0.0/16")
    req = _request("172.20.0.5", xff="100.101.102.103, 172.20.0.1")
    assert client_ip(req) == "100.101.102.103"


def test_xff_klien_palsu_di_kiri_tidak_dipakai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", "172.20.0.0/16")
    req = _request("172.20.0.5", xff="1.2.3.4, 203.0.113.7, 172.20.0.1")
    assert client_ip(req) == "203.0.113.7"


# ---------- dependency + HTTP ----------


def _app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/ping", dependencies=[Depends(rate_limit(GROUP_AUTH))])
    def ping() -> dict[str, bool]:
        return {"ok": True}

    return app


@pytest.fixture
def small_limit() -> _Clock:
    clock = _Clock()
    set_limiter(TokenBucketLimiter({GROUP_AUTH: 2}, clock=clock))
    yield clock
    set_limiter(None)


def test_enforce_menolak_429_dengan_retry_after(
    monkeypatch: pytest.MonkeyPatch, small_limit: _Clock
) -> None:
    monkeypatch.setattr(settings, "RATE_LIMIT_ENFORCE", True)
    client = TestClient(_app())

    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    resp = client.get("/ping")

    assert resp.status_code == 429
    assert int(resp.headers["Retry-After"]) >= 1
    body = resp.json()["error"]
    assert body["code"] == "TOO_MANY_REQUESTS"
    assert body["details"]["retry_after_seconds"] == int(resp.headers["Retry-After"])


def test_catat_saja_tidak_menolak_dan_mencatat_warning(
    monkeypatch: pytest.MonkeyPatch, small_limit: _Clock, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(settings, "RATE_LIMIT_ENFORCE", False)
    client = TestClient(_app())

    with caplog.at_level(logging.WARNING, logger="app.core.rate_limit"):
        codes = [client.get("/ping").status_code for _ in range(4)]

    assert codes == [200, 200, 200, 200]
    assert "Retry-After" not in client.get("/ping").headers
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING and "rate limit" in r.getMessage()]
    assert len(warnings) >= 2


def test_batas_per_pengguna_berlaku_walau_ip_berganti(
    monkeypatch: pytest.MonkeyPatch, small_limit: _Clock
) -> None:
    monkeypatch.setattr(settings, "RATE_LIMIT_ENFORCE", True)
    ips = iter(["198.51.100.1", "198.51.100.2", "198.51.100.3"])
    monkeypatch.setattr(rl, "client_ip", lambda _req: next(ips))
    monkeypatch.setattr(rl, "_user_id", lambda _req: "user-1")
    client = TestClient(_app())

    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 429  # IP baru, tetapi bucket pengguna sudah habis


def test_token_tidak_sah_tidak_memberi_identitas() -> None:
    assert rl._user_id(_request("198.51.100.1", authorization="Bearer ini-bukan-jwt")) is None
    assert rl._user_id(_request("198.51.100.1", authorization="Basic abc")) is None


# ---------- rute yang dilindungi ----------


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/auth/login"),
        ("post", "/auth/refresh"),
        ("post", "/files/upload"),
        ("get", "/files/00000000-0000-0000-0000-000000000001/url"),
        ("put", "/exports/survey-logos/x"),
        ("put", "/teams/00000000-0000-0000-0000-000000000001/logo"),
        ("get", "/face/status"),
    ],
)
def test_rute_yang_dilindungi_kena_429_saat_bucket_habis(
    monkeypatch: pytest.MonkeyPatch, method: str, path: str
) -> None:
    """Dependency dijalankan sebelum validasi/autentikasi: permintaan kedua (limit 1) harus 429."""
    from app.main import API_PREFIX
    from app.main import app as main_app

    groups = (GROUP_AUTH, rl.GROUP_FILE_URL, rl.GROUP_UPLOAD, rl.GROUP_FACE)
    set_limiter(TokenBucketLimiter(dict.fromkeys(groups, 1), clock=_Clock()))
    monkeypatch.setattr(settings, "RATE_LIMIT_ENFORCE", True)
    try:
        client = TestClient(main_app)
        send = getattr(client, method)
        send(f"{API_PREFIX}{path}")  # token pertama (status apa pun, tanpa autentikasi)
        resp = send(f"{API_PREFIX}{path}")
        assert resp.status_code == 429, (path, resp.status_code)
        assert resp.headers.get("Retry-After")
    finally:
        set_limiter(None)
