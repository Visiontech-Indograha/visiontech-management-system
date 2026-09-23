"""
T-14 · MinIO tidak disentuh saat impor (prinsip 3: komponen pendukung mati → pekerjaan lain jalan).
Bucket diperiksa saat pertama dipakai dan hasil suksesnya diingat.
"""
from __future__ import annotations

import importlib
import time

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
