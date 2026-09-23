from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import settings

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


async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session
