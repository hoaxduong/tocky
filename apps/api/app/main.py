from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.database import close_db, init_db
from app.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    await init_db(settings.database_url)
    yield
    await close_db()


app = FastAPI(
    title="Tocky API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
