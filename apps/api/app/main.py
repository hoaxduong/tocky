from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import health, items


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup: initialize resources (DB connections, caches, etc.)
    yield
    # Shutdown: clean up resources


app = FastAPI(
    title="Tocky API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(items.router)
