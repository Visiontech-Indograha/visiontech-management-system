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
# Menetapkan variabel sesi PostgreSQL untuk pelacakan audit. RLS BELUM diaktifkan (belum ada kebijakan);
# variabel ini disiapkan agar kebijakan RLS kelak bisa memakainya.
# Menggunakan SET LOCAL agar efeknya terbatas pada sesi transaksi saat ini.
_SET_CONTEXT = text(
    """
    SELECT set_config('app.user_id', :user_id, true),
           set_config('app.organization_id', :organization_id, true),
           set_config('app.actor_label', :actor_label, true)
    """
)


async def set_request_context(
    db: AsyncSession | AsyncConnection,
    *,
    user_id: str,
    organization_id: str,
    actor_label: str,
) -> None:
    """
    Set context variables (user_id, organization_id, actor_label) in the
    PostgreSQL session for audit triggers (siap dipakai RLS kelak; RLS belum aktif).
    """
    # Mengeksekusi penyiapan variabel sesi secara lokal (SET LOCAL)
    await db.execute(
        _SET_CONTEXT,
        {"user_id": user_id, "organization_id": organization_id, "actor_label": actor_label},
    )
