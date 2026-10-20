"""
Klien HTTP face-service (app/modules/face/services/face_embed_client.py) — tanpa jaringan:
httpx dialihkan ke MockTransport.
Aturan inti: layanan mati/menolak token/error server → FaceServiceUnavailable (absen tetap jalan, hasil SKIPPED);
gambar ditolak (400/413) → ValueError (kesalahan pemanggil); tidak pernah 'sukses' tanpa jawaban layanan.
"""
from __future__ import annotations

import httpx
import pytest

from app.modules.face.services import face_embed_client as fec
from app.modules.face.services.face_embed_client import FaceEmbedClient, FaceServiceUnavailable

pytestmark = pytest.mark.anyio
REAL_CLIENT = httpx.AsyncClient   # asli, diambil sekali: tiap panggilan client_with() memasang pengalih baru

EMBED_OK = {"faces": 1, "embedding": [0.1] * 4, "quality": 0.9, "detection_score": 0.99,
            "model_name": "w600k_mbf", "model_version": "buffalo_s"}


def client_with(monkeypatch, handler, **kw) -> FaceEmbedClient:
    """Klien yang semua permintaan HTTP-nya dijawab `handler(request)`."""
    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return REAL_CLIENT(*args, **kwargs)

    monkeypatch.setattr(fec.httpx, "AsyncClient", factory)
    return FaceEmbedClient(**{"base_url": "http://face:8001", "token": "rahasia", "timeout_s": 2.0, **kw})


async def test_embed_sends_token_and_image_and_parses_result(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["token"] = str(request.url), request.headers.get("x-face-token")
        seen["has_file"] = b"filename=\"probe.jpg\"" in request.content
        return httpx.Response(200, json=EMBED_OK)

    got = await client_with(monkeypatch, handler).embed(b"jpegbytes")
    assert seen == {"url": "http://face:8001/embed", "token": "rahasia", "has_file": True}
    assert got.faces == 1 and got.embedding == [0.1] * 4 and got.model_name == "w600k_mbf"


async def test_embed_without_face_has_no_embedding(monkeypatch):
    body = {**EMBED_OK, "faces": 0, "embedding": None, "quality": None, "detection_score": None}
    got = await client_with(monkeypatch, lambda r: httpx.Response(200, json=body)).embed(b"x")
    assert got.faces == 0 and got.embedding is None


@pytest.mark.parametrize("status", [401, 403, 500, 502, 503, 504])
async def test_embed_service_errors_mean_unavailable(monkeypatch, status):
    with pytest.raises(FaceServiceUnavailable):
        await client_with(monkeypatch, lambda r: httpx.Response(status)).embed(b"x")


@pytest.mark.parametrize("status", [400, 413, 422])
async def test_embed_rejected_image_is_a_caller_error_not_an_outage(monkeypatch, status):
    with pytest.raises(ValueError):
        await client_with(monkeypatch, lambda r: httpx.Response(status)).embed(b"x")


async def test_network_failure_and_timeout_mean_unavailable(monkeypatch):
    def boom(request):
        raise httpx.ConnectError("tak terjangkau")

    def slow(request):
        raise httpx.ReadTimeout("lambat")

    for handler in (boom, slow):
        with pytest.raises(FaceServiceUnavailable):
            await client_with(monkeypatch, handler).embed(b"x")
        with pytest.raises(FaceServiceUnavailable):
            await client_with(monkeypatch, handler).check_challenge(b"x", "kiri")


@pytest.mark.parametrize("kw", [{"base_url": ""}, {"token": ""}])
async def test_not_configured_is_unavailable_without_any_request(monkeypatch, kw):
    called = []

    def handler(request):
        called.append(request)
        return httpx.Response(200, json=EMBED_OK)

    client = client_with(monkeypatch, handler, **kw)
    with pytest.raises(FaceServiceUnavailable):
        await client.embed(b"x")
    with pytest.raises(FaceServiceUnavailable):
        await client.check_challenge(b"x", "kiri")
    assert called == []


async def test_check_challenge_posts_challenge_and_returns_verdict(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["token"] = str(request.url), request.headers.get("x-face-token")
        seen["challenge"] = b"name=\"challenge\"\r\n\r\nkiri" in request.content
        return httpx.Response(200, json={"status": "menunggu", "detail": "Tengok lagi ke KIRI sedikit.",
                                         "metrics": {"yaw": 5.0}})

    got = await client_with(monkeypatch, handler).check_challenge(b"jpeg", "kiri")
    assert seen == {"url": "http://face:8001/challenge-check", "token": "rahasia", "challenge": True}
    assert got["status"] == "menunggu" and got["metrics"] == {"yaw": 5.0}


async def test_check_challenge_error_mapping(monkeypatch):
    with pytest.raises(FaceServiceUnavailable):
        await client_with(monkeypatch, lambda r: httpx.Response(503)).check_challenge(b"x", "kiri")
    with pytest.raises(ValueError):
        await client_with(monkeypatch, lambda r: httpx.Response(400)).check_challenge(b"x", "kiri")


def test_trailing_slash_in_base_url_is_ignored():
    assert FaceEmbedClient(base_url="http://face:8001/", token="t").base_url == "http://face:8001"
