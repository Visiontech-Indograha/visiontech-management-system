from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db_session():
    async with AsyncSessionLocal() as session:
        # Example middleware for SET LOCAL
        # await session.execute(text(f"SET LOCAL vms.user_id = '{current_user_id}'"))
        yield session
