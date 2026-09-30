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
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def execute(self, query: str, params: dict[str, Any] | None = None) -> Any:
        return await self.db.execute(text(query), params or {})

    async def fetchone(self, query: str, params: dict[str, Any] | None = None) -> Any:
        result = await self.db.execute(text(query), params or {})
        return result.fetchone()

    async def fetchall(self, query: str, params: dict[str, Any] | None = None) -> Sequence[Any]:
        result = await self.db.execute(text(query), params or {})
        return result.fetchall()

    async def scalar(self, query: str, params: dict[str, Any] | None = None) -> Any:
        result = await self.db.execute(text(query), params or {})
        return result.scalar()
