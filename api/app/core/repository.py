"""
app/core/repository.py

Kelas dasar untuk semua repositori akses basis data di VMS V2/V3.
Menyediakan helper eksekusi SQL asinkron dengan parameter binding statis.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """
    Kelas dasar untuk semua repositori domain VMS.
    Menyediakan metode pembantu untuk mengeksekusi query SQL mentah terparameterisasi.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def execute(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """Mengeksekusi kueri SQL (INSERT, UPDATE, DELETE) tanpa mengambil baris hasil."""
        return await self.db.execute(text(query), params or {})

    async def fetchone(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """Mengeksekusi kueri SQL dan mengambil satu baris pertama."""
        result = await self.db.execute(text(query), params or {})
        return result.fetchone()

    async def fetchall(self, query: str, params: dict[str, Any] | None = None) -> Sequence[Any]:
        """Mengeksekusi kueri SQL dan mengambil semua baris hasil."""
        result = await self.db.execute(text(query), params or {})
        return result.fetchall()

    async def scalar(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """Mengeksekusi kueri SQL dan mengambil nilai skalar (kolom pertama baris pertama)."""
        result = await self.db.execute(text(query), params or {})
        return result.scalar()


_IDENT = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def safe_columns(keys: Iterable[str]) -> list[str]:
    """Pastikan nama kolom pada UPDATE dinamis hanyalah identifier SQL biasa (cegah injeksi lewat kunci dict)."""
    cols = list(keys)
    bad = [k for k in cols if not _IDENT.match(k)]
    if bad:
        raise ValueError(f"Nama kolom tidak valid: {bad[0]!r}")
    return cols


def escape_like(term: str | None) -> str | None:
    """Netralkan wildcard LIKE (persen, garis bawah, backslash) pada kata kunci pengguna."""
    if term is None:
        return None
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# Alias kompatibilitas
CRUDBase = BaseRepository
