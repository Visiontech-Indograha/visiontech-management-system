"""
app/crud/base.py
Kelas dasar untuk semua crud. Menyediakan helper umum.
Repository adalah satu-satunya tempat query SQL ditulis — lihat docs/12-STANDAR-BACKEND.md.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class CRUDBase:
    """
    Kelas dasar untuk semua operasi CRUD.
    Menyediakan metode pembantu (helper) untuk mengeksekusi query SQL secara asinkron.
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Inisialisasi instance CRUDBase.

        Args:
            db (AsyncSession): Sesi database asinkron dari SQLAlchemy.
        """
        self.db = db

    async def execute(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """
        Mengeksekusi query SQL (seperti INSERT, UPDATE, DELETE) tanpa harus mengambil baris hasil.

        Args:
            query (str): Query SQL mentah.
            params (dict[str, Any] | None): Parameter terikat untuk query. Defaults to None.

        Returns:
            Any: Objek hasil eksekusi (CursorResult).
        """
        # Mengeksekusi teks SQL menggunakan koneksi database saat ini
        return await self.db.execute(text(query), params or {})

    async def fetchone(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """
        Mengeksekusi query SQL dan mengambil satu baris pertama dari hasilnya.

        Args:
            query (str): Query SQL mentah (biasanya SELECT).
            params (dict[str, Any] | None): Parameter terikat untuk query. Defaults to None.

        Returns:
            Any: Satu baris data (Row) atau None jika tidak ada hasil.
        """
        # Mengeksekusi teks SQL dan mengembalikan satu baris pertama
        result = await self.db.execute(text(query), params or {})
        return result.fetchone()

    async def fetchall(self, query: str, params: dict[str, Any] | None = None) -> Sequence[Any]:
        """
        Mengeksekusi query SQL dan mengambil semua baris hasilnya.

        Args:
            query (str): Query SQL mentah (biasanya SELECT).
            params (dict[str, Any] | None): Parameter terikat untuk query. Defaults to None.

        Returns:
            Sequence[Any]: Daftar baris data (Row) dari hasil query.
        """
        # Mengeksekusi teks SQL dan mengembalikan seluruh baris yang ditemukan
        result = await self.db.execute(text(query), params or {})
        return result.fetchall()

    async def scalar(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """
        Mengeksekusi query SQL dan mengambil nilai skalar (kolom pertama dari baris pertama).
        Berguna untuk query agregasi seperti COUNT(), MAX(), dll.

        Args:
            query (str): Query SQL mentah.
            params (dict[str, Any] | None): Parameter terikat untuk query. Defaults to None.

        Returns:
            Any: Nilai tunggal, atau None jika tidak ada baris yang dikembalikan.
        """
        # Mengeksekusi teks SQL dan mengembalikan nilai skalar (kolom pertama, baris pertama)
        result = await self.db.execute(text(query), params or {})
        return result.scalar()
