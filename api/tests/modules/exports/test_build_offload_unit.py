"""
api/tests/modules/exports/test_build_offload_unit.py

Uji unit tanpa DB: builder dokumen sinkron dijalankan di threadpool (bukan di thread event loop),
hasil dikembalikan apa adanya, dan jumlah builder yang berjalan bersamaan dibatasi semafor.
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

import pytest

from app.modules.exports.services import export_service as es


@pytest.mark.asyncio
async def test_build_runs_off_event_loop_thread() -> None:
    loop_thread = threading.get_ident()
    seen: dict[str, int] = {}

    def builder(data: Any) -> bytes:
        seen["thread"] = threading.get_ident()
        return b"ok:" + data

    assert await es._build(builder, b"x") == b"ok:x"
    assert seen["thread"] != loop_thread


@pytest.mark.asyncio
async def test_build_propagates_exception() -> None:
    def builder(_: Any) -> bytes:
        raise ValueError("rusak")

    with pytest.raises(ValueError, match="rusak"):
        await es._build(builder, None)


@pytest.mark.asyncio
async def test_build_concurrency_is_bounded_and_loop_stays_responsive() -> None:
    running = 0
    peak = 0
    guard = threading.Lock()

    def slow_builder(_: Any) -> bytes:
        nonlocal running, peak
        with guard:
            running += 1
            peak = max(peak, running)
        time.sleep(0.05)
        with guard:
            running -= 1
        return b"done"

    ticks = 0

    async def heartbeat() -> None:
        nonlocal ticks
        for _ in range(5):
            await asyncio.sleep(0.01)
            ticks += 1

    results, _ = await asyncio.gather(
        asyncio.gather(*(es._build(slow_builder, None) for _ in range(6))),
        heartbeat(),
    )
    assert results == [b"done"] * 6
    assert peak <= es.EXPORT_BUILD_CONCURRENCY
    assert ticks == 5
