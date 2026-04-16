import ssl as _ssl
from collections.abc import AsyncIterator
from urllib.parse import parse_qs, urlparse, urlunparse

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


def _prepare_url(database_url: str) -> tuple[str, dict]:
    """Strip query params asyncpg can't handle and return (clean_url, kwargs).

    Neon URLs include ?sslmode=require&channel_binding=require which asyncpg
    rejects. We strip them and pass SSL via connect_args instead.
    """
    parsed = urlparse(database_url)
    params = parse_qs(parsed.query)
    needs_ssl = params.pop("sslmode", [None])[0] in ("require", "verify-full")
    needs_ssl = needs_ssl or params.pop("ssl", [None])[0] in ("require", "true")
    params.pop("channel_binding", None)

    # Rebuild URL without stripped params
    remaining = "&".join(f"{k}={v[0]}" for k, v in params.items())
    clean_url = urlunparse(parsed._replace(query=remaining))

    kwargs: dict = {}
    if needs_ssl:
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
        kwargs["connect_args"] = {"ssl": ctx}

    return clean_url, kwargs


async def init_db(database_url: str) -> None:
    global engine, async_session_factory
    clean_url, kwargs = _prepare_url(database_url)
    engine = create_async_engine(clean_url, **kwargs)
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
