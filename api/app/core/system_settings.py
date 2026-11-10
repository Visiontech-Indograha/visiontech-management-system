"""
Setelan sistem yang boleh diubah saat server berjalan (tabel `system_setting`).

Urutan prioritas nilai efektif (tinggi -> rendah):
1. Override darurat env `SYSTEM_SETTINGS_FORCE` ("KUNCI=nilai,KUNCI=nilai"): mengunci nilai (tak bisa diubah lewat API).
2. Baris di tabel `system_setting` (diubah SUPER_ADMIN lewat PUT /system/settings).
3. Env biasa (mis. `ROLE_ASSIGNMENT_ENABLED`) sebagai bawaan: tanpa baris di tabel, perilaku sama dengan dulu.

Pembacaan sinkron dari cache per proses (`get_bool`). Cache diisi saat startup dan disegarkan tiap
`REFRESH_SECONDS` (<= 30 dtk, batas keterlambatan proses lain), serta langsung di proses yang menyimpan.
Hanya flag yang aman diubah saat jalan didaftarkan di `SPECS`.
"""
from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

REFRESH_SECONDS = 15
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


@dataclass(frozen=True)
class SettingSpec:
    key: str
    label: str
    description: str
    env_attr: str | None  # nama atribut `settings` sebagai bawaan; None = bawaan False


SPECS: dict[str, SettingSpec] = {
    "ROLE_ASSIGNMENT_ENABLED": SettingSpec(
        "ROLE_ASSIGNMENT_ENABLED", "Peran ganda dan penugasan kantor",
        "Bila aktif, izin dan cakupan kantor memakai gabungan peran utama dan peran tambahan (ADR 0002).",
        "ROLE_ASSIGNMENT_ENABLED",
    ),
    "RATE_LIMIT_ENFORCE": SettingSpec(
        "RATE_LIMIT_ENFORCE", "Batas laju permintaan",
        "Bila aktif, permintaan berlebihan ditolak 429. Bila mati, hanya dicatat di log.",
        "RATE_LIMIT_ENFORCE",
    ),
}

_cache: dict[str, bool] = {}


def _parse_bool(raw: str) -> bool | None:
    v = raw.strip().lower()
    return True if v in _TRUE else False if v in _FALSE else None


def forced() -> dict[str, bool]:
    """Override darurat dari env; entri tak dikenal atau tak valid diabaikan."""
    out: dict[str, bool] = {}
    for part in settings.SYSTEM_SETTINGS_FORCE.split(","):
        key, sep, raw = part.partition("=")
        key = key.strip()
        value = _parse_bool(raw) if sep else None
        if key in SPECS and value is not None:
            out[key] = value
    return out


def env_default(key: str) -> bool:
    attr = SPECS[key].env_attr
    return bool(getattr(settings, attr)) if attr else False


def source_of(key: str) -> str:
    if key in forced():
        return "env_force"
    return "db" if key in _cache else "env_default"


def get_bool(key: str) -> bool:
    force = forced()
    if key in force:
        return force[key]
    if key in _cache:
        return _cache[key]
    return env_default(key)


def role_assignment_enabled() -> bool:
    return get_bool("ROLE_ASSIGNMENT_ENABLED")


def rate_limit_enforce() -> bool:
    return get_bool("RATE_LIMIT_ENFORCE")


def set_cached(values: Mapping[str, bool]) -> None:
    _cache.update(values)


def reset_cache() -> None:
    _cache.clear()


def _replace_cache(values: Mapping[str, bool]) -> None:
    _cache.clear()
    _cache.update(values)


async def refresh(db: AsyncSession) -> None:
    """Muat ulang cache dari tabel (hanya kunci terdaftar dan bertipe bool)."""
    rows = (await db.execute(text("SELECT key, value FROM system_setting"))).all()
    _replace_cache({k: v for k, v in rows if k in SPECS and isinstance(v, bool)})


async def refresh_safely() -> None:
    """Untuk startup dan tugas latar: galat (mis. tabel belum ada) hanya dicatat; nilai lama dipertahankan."""
    from app.database.session import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            await refresh(db)
    except Exception:
        logger.warning("Gagal memuat system_setting; memakai nilai env/cache lama", exc_info=True)
