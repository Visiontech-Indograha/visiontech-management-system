"""Koneksi aplikasi harus bisa memanggil fungsi skema yang menyebut tabel tanpa awalan `vms.`."""
from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.pool import NullPool

from app.database.session import make_engine
from tests.conftest import requires_db

pytestmark = requires_db


def test_app_connection_can_call_unqualified_schema_functions():
    async def run() -> tuple[str, bool]:
        engine = make_engine(poolclass=NullPool)
        try:
            async with engine.connect() as conn:
                path = (await conn.execute(text("SHOW search_path"))).scalar()
                locked = (await conn.execute(text("SELECT vms.login_is_locked('tidak-ada@contoh.test')"))).scalar()
                return path, locked
        finally:
            await engine.dispose()

    path, locked = asyncio.run(run())

    assert path.replace(" ", "") == "vms,public"
    assert locked is False
