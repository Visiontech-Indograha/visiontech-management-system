from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

from fastapi import Depends

async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session

async def get_db_session_for_user(
    # avoid circular import by local import or type hints
):
    pass # Will implement properly in dependencies

