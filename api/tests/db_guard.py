"""Penjaga DB uji (A-00, docs/24): suite pernah menulis data uji ke DB produksi karena memakai
`DATABASE_URL` dari `api/.env`. Modul ini sengaja tidak mengimpor `app` agar bisa dipakai
`conftest.py` sebelum pengaturan aplikasi dimuat."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "db", "postgres"}
_LOOPBACK = {"localhost", "127.0.0.1", "::1"}
_PROD_MINIO_PORTS = {9000, 9001}   # MinIO produksi (docs/24 A-00); MinIO uji server = :9100
ENV_TEST_FILE = Path(__file__).resolve().parent.parent / ".env.test"


def unsafe_test_database(url: str) -> str | None:
    """None bila aman; selain itu alasan penolakan. Aman = host lokal (CI) atau nama DB berakhiran `_test`."""
    parsed = urlparse(url.replace("+asyncpg", ""))
    host = (parsed.hostname or "").lower()
    name = parsed.path.lstrip("/")
    if host in _LOCAL_HOSTS or name.endswith("_test"):
        return None
    return (f"DB uji '{name}' di {host}:{parsed.port or 5432} bukan DB lokal atau '*_test' — "
            "kemungkinan DB produksi. Set TEST_DATABASE_URL (lihat api/.env.test, docs/24 T0).")


def unsafe_test_storage(endpoint: str) -> str | None:
    """None bila aman. MinIO jarak jauh di port produksi (9000/9001) ditolak; lokal/port uji boleh."""
    parsed = urlparse(f"//{endpoint}")
    host = (parsed.hostname or "").lower()
    if host in _LOOPBACK or (parsed.port or 9000) not in _PROD_MINIO_PORTS:
        return None
    return (f"MinIO uji {endpoint} kemungkinan MinIO produksi. Set MINIO_* di api/.env.test "
            "ke MinIO uji (docs/24 T0).")


def use_test_database() -> str:
    """Arahkan `DATABASE_URL` ke DB uji sebelum `app.core.config` dimuat. → URL yang dipakai."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url and ENV_TEST_FILE.exists():
        for line in ENV_TEST_FILE.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            key = key.strip()
            if key == "TEST_DATABASE_URL":
                url = value.strip()
            elif key.startswith("MINIO_"):
                os.environ.setdefault(key, value.strip())
    if url:
        os.environ["DATABASE_URL"] = url
    return os.environ.get("DATABASE_URL", "")
