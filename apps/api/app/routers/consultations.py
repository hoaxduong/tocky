import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func, select

from app.database import async_session_factory
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

router = APIRouter(prefix="/consultations", tags=["consultations"])


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
    assert async_session_factory is not None

    async def _process_upload() -> None:
        pcm_audio = await convert_to_pcm(file_bytes)
        processor = BatchAudioProcessor(
            consultation_id=consultation_id,
            language=consultation.language,
            model_client=dashscope_client,
            db_session_factory=async_session_factory,
        )
        await processor.process(pcm_audio)

    background_tasks.add_task(_process_upload)
    return ConsultationResponse.model_validate(consultation)


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
