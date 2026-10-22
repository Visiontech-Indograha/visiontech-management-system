"""
app/core/lifespan.py

Lifespan context manager untuk inisialisasi startup dan pembersihan shutdown.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §3 & §11.
"""
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Mengelola siklus hidup aplikasi FastAPI (startup dan shutdown).
    """
    logger.info("Aplikasi VMS FastAPI memulai lifecycle startup.")
    try:
        from app.database.migration_v3 import apply_v3_migrations
        await apply_v3_migrations()
    except Exception as e:  # noqa: BLE001
        logger.error("Gagal menjalankan migrasi VMS V3 pada startup: %s", e)
    yield
    logger.info("Aplikasi VMS FastAPI menyelesaikan lifecycle shutdown.")


