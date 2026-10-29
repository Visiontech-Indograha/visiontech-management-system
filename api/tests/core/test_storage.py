"""
T-14 · MinIO tidak disentuh saat impor (prinsip 3: komponen pendukung mati → pekerjaan lain jalan).
Bucket diperiksa saat pertama dipakai dan hasil suksesnya diingat.
"""
from __future__ import annotations

import importlib
import time
from types import SimpleNamespace

import pytest
from minio import Minio

from app.core import storage


@pytest.fixture
def fresh_storage(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("MinIO tidak boleh dihubungi saat impor")

    monkeypatch.setattr(Minio, "bucket_exists", forbidden)
    module = importlib.reload(storage)
    yield module
    monkeypatch.undo()
    importlib.reload(storage)


def test_import_does_not_contact_minio(fresh_storage):
    assert fresh_storage.bucket_ready() is False


def test_bucket_is_checked_once_then_remembered(fresh_storage, monkeypatch):
    calls = {"exists": 0, "put": 0}

    def exists(bucket: str) -> bool:
        calls["exists"] += 1
        return True

    def put(*args, **kwargs) -> None:
        calls["put"] += 1

    monkeypatch.setattr(fresh_storage.minio_client, "bucket_exists", exists)
    monkeypatch.setattr(fresh_storage.minio_client, "put_object", put)

    assert fresh_storage.upload_file("a.webp", b"x", "image/webp") is True
    assert fresh_storage.upload_file("b.webp", b"y", "image/webp") is True
    assert calls == {"exists": 1, "put": 2}


def test_minio_down_fails_fast_and_is_retried_later(fresh_storage, monkeypatch):
    def down(bucket: str) -> bool:
        raise ConnectionError("MinIO mati")

    monkeypatch.setattr(fresh_storage.minio_client, "bucket_exists", down)

    started = time.monotonic()
    assert fresh_storage.upload_file("a.webp", b"x", "image/webp") is False
    assert time.monotonic() - started < 1
    assert fresh_storage.bucket_ready() is False  # kegagalan tidak diingat; percobaan berikut mencoba lagi


def test_client_uses_short_timeouts():
    pool = storage.minio_client._http
    assert pool.connection_pool_kw["timeout"].connect_timeout <= 3
    assert pool.connection_pool_kw["retries"].total <= 1


# ── URL presigned untuk peramban/HP (temuan audit R-18) ────────────────────────────────────────
def test_presigned_url_uses_public_origin_when_configured(monkeypatch):
    """Produksi: CSP web `img-src 'self'` dan MinIO tanpa port publik → URL presigned harus dibuat
    untuk domain aplikasi (Caddy meneruskan /<bucket>/* ke MinIO). Tanda tangan S3 mengikat host,
    jadi host tidak bisa sekadar ditulis ulang setelahnya. Tidak ada panggilan jaringan (region tetap)."""
    monkeypatch.setattr(storage.settings, "MINIO_PUBLIC_URL", "https://vms.contoh.id")
    import urllib3

    def no_network(*a, **k):
        raise AssertionError("penandatanganan URL tidak boleh menghubungi MinIO")

    monkeypatch.setattr(urllib3.PoolManager, "urlopen", no_network)
    storage.presign_client.cache_clear()
    try:
        url = storage.get_presigned_url("org/berkas_view.webp")
    finally:
        storage.presign_client.cache_clear()

    assert url.startswith(f"https://vms.contoh.id/{storage.settings.MINIO_BUCKET}/org/berkas_view.webp?")
    assert "X-Amz-Signature=" in url and "X-Amz-Expires=300" in url


def test_presigned_url_defaults_to_internal_endpoint(monkeypatch):
    monkeypatch.setattr(storage.settings, "MINIO_PUBLIC_URL", "")
    storage.presign_client.cache_clear()
    try:
        assert storage.presign_client() is storage.minio_client
    finally:
        storage.presign_client.cache_clear()


# ── Logo pengganti belum diunggah: NoSuchKey harus fallback senyap (bukan ERROR) ────────────────
def test_logo_belum_diunggah_fallback_tanpa_error(monkeypatch, caplog):
    import logging

    from minio.error import S3Error

    from app.shared.documents import branding

    monkeypatch.setattr(storage, "ensure_bucket", lambda: True)

    def no_such_key(bucket: str, object_name: str):
        raise S3Error("NoSuchKey", "The specified key does not exist.", object_name, "rid", "hid",
                      SimpleNamespace(status=404, headers={}), bucket_name=bucket, object_name=object_name)

    monkeypatch.setattr(storage.minio_client, "get_object", no_such_key)
    with caplog.at_level(logging.DEBUG, logger="app.core.storage"):
        assert branding.custom_logos("org-uji") == {}
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
