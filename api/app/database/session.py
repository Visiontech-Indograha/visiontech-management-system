"""
app/database/session.py

Database connections and sessions.
Configures async engine, session makers, transaction boundaries, and request
context (variabel sesi untuk audit; RLS BELUM aktif, lihat catatan di bawah).
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.errors import AppError
from app.core.events import discard_events, flush_events

# ── Engine & sessions ────────────────────────────────────────────────────────────
# Fungsi & trigger di db/*.sql menyebut tabel tanpa awalan skema,
# jadi setiap koneksi aplikasi wajib memakai path yang sama.
SEARCH_PATH = "public, vms"


def make_engine(url: str | None = None, **kwargs: Any) -> AsyncEngine:
    """
    Create and configure the SQLAlchemy AsyncEngine. `url` kosong → DATABASE_URL (koneksi API).
    Dilengkapi pool_pre_ping dan pool_recycle untuk stabilitas koneksi jaringan database.
    """
    engine_kwargs: dict[str, Any] = {
        "echo": False,
        # Nilai parameter SQL (NIK, rekening, sandi, token) tidak boleh tercetak di galat/log.
        "hide_parameters": True,
        "connect_args": {
            "server_settings": {
                "search_path": SEARCH_PATH,
                "timezone": "Asia/Jakarta",
            }
        },
    }
    # Parameter pool_size & max_overflow hanya untuk queue pool (bukan NullPool pada uji coba)
    poolclass = kwargs.get("poolclass")
    is_null_pool = poolclass is not None and getattr(poolclass, "__name__", "") == "NullPool"
    if not is_null_pool:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 1800
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20

    engine_kwargs.update(kwargs)
    return create_async_engine(url or settings.DATABASE_URL, **engine_kwargs)


engine = make_engine()
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """
    Yield an async database session for the dependency injection system.
    """
    # Memberikan sesi database async
    async with AsyncSessionLocal() as session:
        yield session


# ── Transaction boundaries ───────────────────────────────────────────────────
# Satu permintaan atau kasus pakai dibatasi dalam satu transaksi.
@asynccontextmanager
async def unit_of_work(db: AsyncSession) -> AsyncIterator[None]:
    """
    Manage the transaction boundary for a unit of work.
    Commits if the block completes successfully, rolls back on exceptions.
    Handles AppError with `persist=True` by committing before re-raising.
    """
    try:
        # Menjalankan blok operasi dalam unit transaksi
        yield
    except AppError as exc:
        # Jika persist=True, simpan perubahan sebelum membuang galat
        if exc.persist:
            await db.commit()
            flush_events(db)
        else:
            await db.rollback()
            discard_events(db)
        raise
    except BaseException:
        # Kembalikan perubahan jika terjadi kesalahan lain
        await db.rollback()
        discard_events(db)
        raise
    else:
        # Simpan perubahan jika tidak ada kesalahan, lalu siarkan peristiwa realtime (hanya setelah commit)
        await db.commit()
        flush_events(db)


# ── Request context (audit; RLS belum aktif) ─────────────────────────────────
# Menetapkan variabel sesi PostgreSQL untuk pelacakan audit dan fondasi RLS.
# Menggunakan SET LOCAL (is_local=true) agar efeknya terbatas pada sesi transaksi saat ini.
_SET_CONTEXT = text(
    """
    SELECT set_config('app.user_id', CAST(:user_id AS text), true),
           set_config('app.organization_id', CAST(:organization_id AS text), true),
           set_config('app.org_id', CAST(:org_id AS text), true),
           set_config('app.actor_label', CAST(:actor_label AS text), true),
           set_config('app.role', CAST(:role AS text), true),
           set_config('app.office_id', CAST(:office_id AS text), true),
           set_config('app.division_id', CAST(:division_id AS text), true),
           set_config('app.is_system', CAST(:is_system AS text), true)
    """
)


async def set_request_context(
    db: AsyncSession | AsyncConnection,
    *,
    user_id: str | UUID | None = None,
    organization_id: str | UUID | None = None,
    org_id: str | UUID | None = None,
    actor_label: str | None = None,
    role: str | None = None,
    office_id: str | UUID | None = None,
    division_id: str | UUID | None = None,
    is_system: bool | str | None = False,
) -> None:
    """
    Set context variables (user_id, org_id, actor_label, role, office_id, division_id, is_system)
    in the PostgreSQL session for audit triggers and upcoming RLS policies.
    Menggunakan SET LOCAL (is_local=true) agar terisolasi pada transaksi saat ini
    dan tidak bocor ke permintaan lain pada koneksi pool yang sama.
    """
    org_val = organization_id if organization_id is not None else org_id
    org_str = str(org_val) if org_val is not None else None
    sys_str = "1" if (is_system is True or is_system == "1") else "0"

    params: dict[str, Any] = {
        "user_id": str(user_id) if user_id is not None else None,
        "organization_id": org_str,
        "org_id": org_str,
        "actor_label": str(actor_label) if actor_label is not None else None,
        "role": str(role) if role is not None else None,
        "office_id": str(office_id) if office_id is not None else None,
        "division_id": str(division_id) if division_id is not None else None,
        "is_system": sys_str,
    }
    await db.execute(_SET_CONTEXT, params)
