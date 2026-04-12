from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import close_db, init_db
from app.routers import (
    admin,
    auth,
    consultations,
    health,
    scribe_ws,
    soap_notes,
    transcripts,
)
from app.services.dashscope_client import DashScopeClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    await init_db(settings.database_url)

    fallback = settings.qwen_model_name
    app.state.dashscope_client = DashScopeClient(
        base_url=settings.dashscope_base_url,
        api_key=settings.dashscope_api_key,
        transcription_model=settings.qwen_transcription_model or fallback,
        classification_model=settings.qwen_classification_model or fallback,
        soap_model=settings.qwen_soap_model or fallback,
        extraction_model=settings.qwen_extraction_model or fallback,
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
api_v1.include_router(admin.router)
app.include_router(api_v1)

# WebSocket (unversioned)
app.include_router(scribe_ws.router)
