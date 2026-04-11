from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

engine = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    pass


async def init_db(database_url: str) -> None:
    global engine, async_session_factory
    engine = create_async_engine(database_url)
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def close_db() -> None:
    global engine, async_session_factory
    if engine is not None:
        await engine.dispose()
        engine = None
        async_session_factory = None


async def get_db_session() -> AsyncIterator[AsyncSession]:
    assert async_session_factory is not None, "Database not initialized"
    async with async_session_factory() as session:
        yield session
