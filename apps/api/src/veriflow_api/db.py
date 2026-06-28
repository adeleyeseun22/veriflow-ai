from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from veriflow_api.config import settings


engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.debug,
)


async def check_database() -> None:
    """Raise an exception when PostgreSQL is unavailable."""

    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
