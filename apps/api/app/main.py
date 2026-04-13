import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import database as _db
from app.config import get_settings
from app.database import close_db, init_db
from app.routers import (
    admin,
    auth,
    consultations,
    events,
    health,
    scribe_ws,
    soap_notes,
    transcripts,
)
from app.services.dashscope_client import DashScopeClient
from app.services.event_queue import EventQueueRegistry
from app.services.oss_client import OSSClient
from app.services.prompt_registry import PromptRegistry


def _configure_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quiet noisy third-party loggers even in debug mode
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("hpack").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    _configure_logging(settings.debug)
    await init_db(settings.database_url)

    prompt_registry = PromptRegistry()
    await prompt_registry.load(_db.async_session_factory)
    app.state.prompt_registry = prompt_registry

    fallback = settings.qwen_model_name
    app.state.event_registry = EventQueueRegistry()
    app.state.background_tasks = set()  # prevent GC of asyncio tasks

    app.state.dashscope_client = DashScopeClient(
        base_url=settings.dashscope_base_url,
        api_key=settings.dashscope_api_key,
        transcription_model=settings.qwen_transcription_model or fallback,
        classification_model=settings.qwen_classification_model or fallback,
        soap_model=settings.qwen_soap_model or fallback,
        extraction_model=settings.qwen_extraction_model or fallback,
        prompt_registry=prompt_registry,
    )

    app.state.oss_client = OSSClient(
        access_key_id=settings.oss_access_key_id,
        access_key_secret=settings.oss_access_key_secret,
        endpoint=settings.oss_endpoint,
        bucket_name=settings.oss_bucket_name,
    )

    yield

    await app.state.dashscope_client.close()
    await close_db()


app = FastAPI(
    title="Tốc ký AI API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["set-cookie"],
)

# Health check (unversioned)
app.include_router(health.router)

# Versioned REST API
api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(auth.router)
api_v1.include_router(consultations.router)
api_v1.include_router(soap_notes.router)
api_v1.include_router(transcripts.router)
api_v1.include_router(events.router)
api_v1.include_router(admin.router)
app.include_router(api_v1)

# WebSocket (unversioned)
app.include_router(scribe_ws.router)
