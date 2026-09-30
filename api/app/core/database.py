"""
Basis data (docs/12 §1): engine & sesi, batas transaksi, dan konteks RLS permintaan.
Dipindah dari `app/db/{session,transaction,context}.py` (R-28 M1) tanpa perubahan perilaku.
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

# ── Engine & sesi ────────────────────────────────────────────────────────────
# Fungsi & trigger di db/*.sql menyebut tabel tanpa awalan skema (ditulis dengan
# `SET search_path = vms, public`), jadi setiap koneksi aplikasi wajib memakai path yang sama.
SEARCH_PATH = "vms, public"


def make_engine(**kwargs: Any) -> AsyncEngine:
    return create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"server_settings": {"search_path": SEARCH_PATH}},
        **kwargs,
    )


engine = make_engine()
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


# ── Batas transaksi ──────────────────────────────────────────────────────────
# Dok 12 §2: satu permintaan / satu kasus pakai = satu transaksi.
# Dipakai dependency sesi (app/api/deps.py::get_db) dan controller.
@asynccontextmanager
async def unit_of_work(db: AsyncSession) -> AsyncIterator[None]:
    """
    Commit bila kasus pakai selesai; rollback bila gagal.
    AppError dengan `persist=True` tetap di-commit sebelum galatnya diteruskan ke klien.
    """
    try:
        yield
    except AppError as exc:
        if exc.persist:
            await db.commit()
        else:
            await db.rollback()
        raise
    except BaseException:
        await db.rollback()
        raise
    else:
        await db.commit()


# ── Konteks permintaan (RLS & audit) ─────────────────────────────────────────
# `app.user_id`, `app.organization_id`, `app.actor_label` — dibaca `current_user_id()`,
# `current_org_id()`, `tg_audit_row()`.
#
# `set_config(..., true)` = SET LOCAL: berlaku sampai transaksi selesai, jadi tidak bocor ke
# permintaan lain yang memakai koneksi yang sama (R-08). Satu `SELECT` dengan parameter bind —
# `SET LOCAL x = $1` tidak bisa dipakai karena SET tidak menerima parameter, dan asyncpg menolak
# beberapa perintah dalam satu prepared statement.
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
    await db.execute(
        _SET_CONTEXT,
        {"user_id": user_id, "organization_id": organization_id, "actor_label": actor_label},
    )
