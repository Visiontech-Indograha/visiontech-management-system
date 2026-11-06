"""
app/shared/documents/build_limiter.py
Batas konkurensi pembangun dokumen berat (PDF/DOCX/PPTX; CPU-bound, memori server 4 GB).
Antre di event loop (asyncio.Semaphore), kerja sinkron dijalankan di threadpool.
"""
from __future__ import annotations

import asyncio
import weakref
from collections.abc import Callable
from typing import Any

EXPORT_BUILD_CONCURRENCY = 2
_SLOTS: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = weakref.WeakKeyDictionary()


def _slots() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    sem = _SLOTS.get(loop)
    if sem is None:
        sem = _SLOTS[loop] = asyncio.Semaphore(EXPORT_BUILD_CONCURRENCY)
    return sem


async def build_limited(builder: Callable[[Any], bytes], data: Any) -> bytes:
    """Tunggu giliran tanpa memblokir thread, lalu jalankan builder sinkron di threadpool."""
    async with _slots():
        return await asyncio.to_thread(builder, data)
