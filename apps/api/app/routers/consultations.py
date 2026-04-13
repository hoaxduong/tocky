import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app import database
from app.db_models.consultation import Consultation
from app.dependencies import CurrentUserDep, DbSessionDep
from app.models.consultation import (
    ConsultationCreate,
    ConsultationListResponse,
    ConsultationResponse,
    ConsultationUpdate,
)
from app.services.audio_converter import convert_to_pcm, validate_audio_file
from app.services.batch_audio_processor import BatchAudioProcessor
from app.services.event_bus import event_bus

router = APIRouter(prefix="/consultations", tags=["consultations"])

# Status values from which resume is allowed.
_RESUMABLE_STATUSES = {"failed", "processing"}


@router.get("/", response_model=ConsultationListResponse)
async def list_consultations(
    db: DbSessionDep,
    user: CurrentUserDep,
    offset: int = 0,
    limit: int = 20,
    status_filter: str | None = None,
):
    query = select(Consultation).where(Consultation.user_id == user["id"])
    if status_filter:
        query = query.where(Consultation.status == status_filter)
    else:
        query = query.where(Consultation.status != "archived")

    total_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_query)).scalar_one()

    query = query.order_by(Consultation.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return ConsultationListResponse(
        items=[ConsultationResponse.model_validate(c) for c in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/",
    response_model=ConsultationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_consultation(
    body: ConsultationCreate,
    db: DbSessionDep,
    user: CurrentUserDep,
    response: Response,
):
    consultation = Consultation(
        user_id=user["id"],
        title=body.title,
        patient_identifier=body.patient_identifier,
        language=body.language,
        mode=body.mode,
        status="uploading" if body.mode == "upload" else "recording",
    )
    db.add(consultation)
    await db.commit()
    await db.refresh(consultation)
    response.headers["Location"] = f"/api/v1/consultations/{consultation.id}"
    return ConsultationResponse.model_validate(consultation)


@router.get("/{consultation_id}", response_model=ConsultationResponse)
async def get_consultation(
    consultation_id: uuid.UUID,
    db: DbSessionDep,
    user: CurrentUserDep,
):
    consultation = await _get_user_consultation(db, consultation_id, user["id"])
    return ConsultationResponse.model_validate(consultation)


@router.patch("/{consultation_id}", response_model=ConsultationResponse)
async def update_consultation(
    consultation_id: uuid.UUID,
    body: ConsultationUpdate,
    db: DbSessionDep,
    user: CurrentUserDep,
):
    consultation = await _get_user_consultation(db, consultation_id, user["id"])
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(consultation, key, value)
    await db.commit()
    await db.refresh(consultation)
    return ConsultationResponse.model_validate(consultation)


@router.post("/{consultation_id}/archive", response_model=ConsultationResponse)
async def archive_consultation(
    consultation_id: uuid.UUID,
    db: DbSessionDep,
    user: CurrentUserDep,
):
    consultation = await _get_user_consultation(db, consultation_id, user["id"])
    if consultation.status == "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consultation is already archived",
        )
    consultation.status = "archived"
    await db.commit()
    await db.refresh(consultation)
    return ConsultationResponse.model_validate(consultation)


@router.delete(
    "/{consultation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_consultation(
    consultation_id: uuid.UUID,
    db: DbSessionDep,
    user: CurrentUserDep,
):
    consultation = await _get_user_consultation(db, consultation_id, user["id"])
    if consultation.status != "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only archived consultations can be deleted",
        )
    await db.delete(consultation)
    await db.commit()


@router.post(
    "/{consultation_id}/upload-audio",
    response_model=ConsultationResponse,
)
async def upload_audio(
    consultation_id: uuid.UUID,
    file: UploadFile,
    request: Request,
    db: DbSessionDep,
    user: CurrentUserDep,
    background_tasks: BackgroundTasks,
):
    consultation = await _get_user_consultation(db, consultation_id, user["id"])
    if consultation.mode != "upload":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consultation is not in upload mode",
        )
    if consultation.status != "uploading":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio has already been uploaded for this consultation",
        )

    validate_audio_file(file.filename or "", file.size or 0)
    file_bytes = await file.read()

    consultation.status = "processing"
    consultation.processing_step = "converting"
    consultation.processing_progress = 0
    await db.commit()
    await db.refresh(consultation)

    dashscope_client = request.app.state.dashscope_client
    oss_client = request.app.state.oss_client
    db_session_factory = database.async_session_factory
    assert db_session_factory is not None

    async def _process_upload() -> None:
        pcm_audio = await convert_to_pcm(file_bytes)
        processor = BatchAudioProcessor(
            consultation_id=consultation_id,
            model_client=dashscope_client,
            db_session_factory=db_session_factory,
            oss_client=oss_client,
        )
        await processor.start(pcm_audio)

    background_tasks.add_task(_process_upload)
    return ConsultationResponse.model_validate(consultation)


@router.post(
    "/{consultation_id}/resume",
    response_model=ConsultationResponse,
)
async def resume_processing(
    consultation_id: uuid.UUID,
    request: Request,
    db: DbSessionDep,
    user: CurrentUserDep,
    background_tasks: BackgroundTasks,
):
    """Resume a failed (or stuck) transcription run from the last checkpoint."""
    consultation = await _get_user_consultation(db, consultation_id, user["id"])
    if consultation.status not in _RESUMABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot resume from status '{consultation.status}'. "
                f"Expected one of: {sorted(_RESUMABLE_STATUSES)}"
            ),
        )
    if consultation.pcm_audio_oss_key is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No persisted audio checkpoint to resume from. "
                "Re-upload the audio to restart processing."
            ),
        )

    consultation.status = "processing"
    consultation.error_message = None
    await db.commit()
    await db.refresh(consultation)

    dashscope_client = request.app.state.dashscope_client
    oss_client = request.app.state.oss_client
    db_session_factory = database.async_session_factory
    assert db_session_factory is not None

    async def _resume() -> None:
        processor = BatchAudioProcessor(
            consultation_id=consultation_id,
            model_client=dashscope_client,
            db_session_factory=db_session_factory,
            oss_client=oss_client,
        )
        await processor.resume()

    background_tasks.add_task(_resume)
    return ConsultationResponse.model_validate(consultation)


@router.get("/{consultation_id}/events")
async def stream_consultation_events(
    consultation_id: uuid.UUID,
    db: DbSessionDep,
    user: CurrentUserDep,
):
    """Server-Sent Events stream of processing progress + transcript updates.

    Emits an initial ``snapshot`` event with the current consultation state so
    clients can render immediately, then forwards events from the background
    processor as they happen. Completes with a ``status: completed`` or
    ``status: failed`` event.
    """
    consultation = await _get_user_consultation(db, consultation_id, user["id"])

    async def event_stream() -> AsyncIterator[bytes]:
        # Initial snapshot so reconnecting clients catch up without polling.
        snapshot = {
            "type": "snapshot",
            "status": consultation.status,
            "step": consultation.processing_step,
            "progress": consultation.processing_progress,
            "chunks_total": consultation.chunks_total,
            "chunks_completed": consultation.chunks_completed,
            "error": consultation.error_message,
        }
        yield _sse_format(snapshot)

        # If the run is already in a terminal state, no need to subscribe.
        if consultation.status in ("completed", "failed"):
            return

        subscription = event_bus.subscribe(consultation_id)
        try:
            async for event in subscription:
                yield _sse_format(event)
                # Close the stream once the run reaches a terminal state.
                if event.get("type") == "status" and event.get("status") in (
                    "completed",
                    "failed",
                ):
                    break
        except asyncio.CancelledError:
            # Client disconnected; processing continues independently.
            raise

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_format(payload: dict) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode()


async def _get_user_consultation(
    db, consultation_id: uuid.UUID, user_id: str
) -> Consultation:
    result = await db.execute(
        select(Consultation).where(
            Consultation.id == consultation_id,
            Consultation.user_id == user_id,
        )
    )
    consultation = result.scalar_one_or_none()
    if consultation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation {consultation_id} not found",
        )
    return consultation
