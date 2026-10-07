"""
app/db/session.py

Database connections and sessions.
Configures async engine, session makers, transaction boundaries, and request
context (Row Level Security - RLS).
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

# ── Engine & sessions ────────────────────────────────────────────────────────────
# Fungsi & trigger di db/*.sql menyebut tabel tanpa awalan skema,
# jadi setiap koneksi aplikasi wajib memakai path yang sama.
SEARCH_PATH = "vms, public"


def make_engine(**kwargs: Any) -> AsyncEngine:
    """
    Create and configure the SQLAlchemy AsyncEngine.
    """
    # Membuat engine async dengan path pencarian yang tepat
    return create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"server_settings": {"search_path": SEARCH_PATH}},
        **kwargs,
    )


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
        else:
            await db.rollback()
        raise
    except BaseException:
        # Kembalikan perubahan jika terjadi kesalahan lain
        await db.rollback()
        raise
    else:
        # Simpan perubahan jika tidak ada kesalahan
        await db.commit()


# ── Request context (RLS & audit) ────────────────────────────────────────────
# Menetapkan variabel lingkungan PostgreSQL untuk RLS dan pelacakan audit.
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
    PostgreSQL session to support Row Level Security (RLS) and audit triggers.
    """
    # Mengeksekusi penyiapan variabel RLS secara lokal
    await db.execute(
        _SET_CONTEXT,
        {"user_id": user_id, "organization_id": organization_id, "actor_label": actor_label},
    )
