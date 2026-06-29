from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from veriflow_api.config import settings

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.debug,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Provide one transactional database session per request."""

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database() -> None:
    """Raise an exception when PostgreSQL is unavailable."""

    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
