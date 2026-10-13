"""Konfigurasi bersama untuk skrip operasional (unggah berkas & impor data).

Nilai rahasia TIDAK boleh ditulis di dalam kode: skrip membaca `api/.env`
(yang di-gitignore) atau variabel lingkungan. Dengan begitu kredensial tidak
pernah masuk riwayat git — aturan git-flow §8.

Urutan pencarian nilai:
1. variabel lingkungan proses (mis. `MINIO_SECRET_KEY=... python skrip.py`)
2. berkas `api/.env`
3. nilai bawaan non-rahasia (hanya host/port/bucket — bukan kata sandi)
"""
from __future__ import annotations

import os
from pathlib import Path

# Akar repo = folder induk folder `scripts/`
REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / "api" / ".env"

_env_cache: dict[str, str] | None = None


def _load_env_file() -> dict[str, str]:
    """Baca api/.env sekali saja; berkas tidak ada = kamus kosong."""
    global _env_cache
    if _env_cache is not None:
        return _env_cache
    values: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            values[key.strip()] = val.strip().strip('"').strip("'")
    _env_cache = values
    return values


def get(name: str, default: str | None = None) -> str:
    """Ambil konfigurasi: lingkungan → api/.env → bawaan.

    `default=None` + nilai tidak ditemukan → RuntimeError dengan pesan yang
    menyebut nama variabelnya, supaya kegagalan jelas, bukan diam-diam salah.
    """
    if name in os.environ and os.environ[name] != "":
        return os.environ[name]
    val = _load_env_file().get(name)
    if val:
        return val
    if default is not None:
        return default
    raise RuntimeError(
        f"Konfigurasi '{name}' tidak ditemukan. Setel di api/.env atau lewat "
        f"variabel lingkungan, mis. {name}=... python skrip.py"
    )


def minio_client():
    """Klien MinIO dari konfigurasi (tanpa kredensial di kode)."""
    from minio import Minio

    endpoint = get("MINIO_ENDPOINT", "127.0.0.1:9100")
    return Minio(
        endpoint,
        access_key=get("MINIO_ACCESS_KEY"),
        secret_key=get("MINIO_SECRET_KEY"),
        secure=get("MINIO_SECURE", "false").lower() == "true",
    )


def minio_bucket() -> str:
    return get("MINIO_BUCKET", "vms-files")


def dsn_psycopg2() -> str:
    """DSN psycopg2 dari DATABASE_URL (asyncpg → psycopg2)."""
    url = get("DATABASE_URL")
    return url.replace("postgresql+asyncpg://", "postgresql://")


__all__ = ["get", "minio_client", "minio_bucket", "dsn_psycopg2", "REPO_ROOT", "ENV_FILE"]
