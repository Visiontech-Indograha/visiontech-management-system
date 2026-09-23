"""
app/db/transaction.py
Batas transaksi (dok 12 §2): satu permintaan / satu kasus pakai = satu transaksi.
Dipakai dependency sesi (app/api/deps.py::get_db) dan controller.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError


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
