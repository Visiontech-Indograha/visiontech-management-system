"""
app/core/lifespan.py

Lifespan context manager untuk inisialisasi startup dan pembersihan shutdown.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §3 & §11.
"""

import asyncio
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
    from app.database.migration_v3 import ensure_activity_log_partitions, prepare_v2_runtime

    await prepare_v2_runtime()

    async def _keep_partitions() -> None:
        # Server yang tidak di-restart berbulan-bulan tetap punya partisi audit bulan berikutnya.
        while True:
            await asyncio.sleep(12 * 3600)
            try:
                await ensure_activity_log_partitions()
            except Exception:
                logger.exception("Pemeliharaan partisi app_activity_logs gagal")

    from app.core import system_settings

    await system_settings.refresh_safely()

    async def _refresh_settings() -> None:
        # Setelan sistem diubah lewat proses lain: cache per proses disegarkan tiap REFRESH_SECONDS (<= 30 dtk).
        while True:
            await asyncio.sleep(system_settings.REFRESH_SECONDS)
            await system_settings.refresh_safely()

    task = asyncio.create_task(_keep_partitions())
    settings_task = asyncio.create_task(_refresh_settings())
    try:
        yield
    finally:
        task.cancel()
        settings_task.cancel()
    logger.info("Aplikasi VMS FastAPI menyelesaikan lifecycle shutdown.")
