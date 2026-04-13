import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import database as _db
from app.config import get_settings
from app.database import close_db, init_db
from app.routers import (
    admin,
    auth,
    consultations,
    events,
    health,
    icd10,
    scribe_ws,
    soap_notes,
    transcripts,
)
from app.services.dashscope_client import DashScopeClient
from app.services.event_queue import EventQueueRegistry
from app.services.local_storage_client import LocalStorageClient
from app.services.oss_client import OSSClient
from app.services.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)


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

    if settings.sandbox_ai:
        from app.services.sandbox_client import SandboxAIClient
        from app.services.sandbox_streaming_stt import SandboxStreamingSTT

        app.state.dashscope_client = SandboxAIClient(
            latency=settings.sandbox_ai_latency,
        )
        app.state.streaming_stt = SandboxStreamingSTT(
            latency=settings.sandbox_ai_latency,
        )
        logger.info("Sandbox AI mode \u2014 no real API calls")
    else:
        from app.services.streaming_stt import DashScopeStreamingSTT

        app.state.dashscope_client = DashScopeClient(
            base_url=settings.dashscope_base_url,
            api_key=settings.dashscope_api_key,
            transcription_model=settings.qwen_transcription_model or fallback,
            classification_model=settings.qwen_classification_model or fallback,
            soap_model=settings.qwen_soap_model or fallback,
            extraction_model=settings.qwen_extraction_model or fallback,
            prompt_registry=prompt_registry,
        )
        app.state.streaming_stt = DashScopeStreamingSTT(
            api_key=settings.dashscope_api_key,
            ws_base_url=settings.dashscope_ws_base_url,
            model=settings.qwen_streaming_asr_model,
            vad_threshold=settings.vad_threshold,
            vad_silence_ms=settings.vad_silence_duration_ms,
            vad_prefix_ms=settings.vad_prefix_padding_ms,
        )

    if settings.oss_endpoint:
        app.state.oss_client = OSSClient(
            access_key_id=settings.oss_access_key_id,
            access_key_secret=settings.oss_access_key_secret,
            endpoint=settings.oss_endpoint,
            bucket_name=settings.oss_bucket_name,
        )
    else:
        storage_dir = Path(__file__).resolve().parents[1] / "storage"
        app.state.oss_client = LocalStorageClient(
            storage_dir=storage_dir,
            base_url="http://localhost:8000",
        )
        logger.info("Using local file storage at %s", storage_dir)

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

_STORAGE_DIR = Path(__file__).resolve().parents[1] / "storage"


@app.get("/storage/{file_path:path}")
async def serve_local_storage(file_path: str):
    """Serve files from local storage (dev only)."""
    full = _STORAGE_DIR / file_path
    if not full.resolve().is_relative_to(_STORAGE_DIR.resolve()):
        raise HTTPException(status_code=403)
    if not full.is_file():
        raise HTTPException(status_code=404)
    suffix = full.suffix.lower()
    media_types = {
        ".wav": "audio/wav",
        ".pcm": "application/octet-stream",
    }
    content_type = media_types.get(suffix, "application/octet-stream")
    return FileResponse(full, media_type=content_type)


# Health check (unversioned)
app.include_router(health.router)

# Versioned REST API
api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(auth.router)
api_v1.include_router(consultations.router)
api_v1.include_router(soap_notes.router)
api_v1.include_router(transcripts.router)
api_v1.include_router(events.router)
api_v1.include_router(icd10.router)
api_v1.include_router(admin.router)
app.include_router(api_v1)

# WebSocket (unversioned)
app.include_router(scribe_ws.router)
