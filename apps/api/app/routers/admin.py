import difflib
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, update

from app.db_models.consultation import Consultation
from app.db_models.prompt_template import PromptTemplate
from app.db_models.session import Session
from app.db_models.user import User
from app.dependencies import AdminUserDep, DbSessionDep
from app.models.consultation import ConsultationListResponse, ConsultationResponse
from app.models.prompt_template import (
    PromptTemplateListResponse,
    PromptTemplateResponse,
    PromptTemplateUpdate,
    PromptVersionListResponse,
)
from app.models.user import (
    BanUserRequest,
    CreateUserRequest,
    UpdateUserRoleRequest,
    UserListResponse,
    UserResponse,
)
from app.services.auth import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])


# --- Consultation endpoints ---


@router.get("/consultations", response_model=ConsultationListResponse)
async def list_all_consultations(
    db: DbSessionDep,
    _user: AdminUserDep,
    offset: int = 0,
    limit: int = 20,
):
    query = select(Consultation)
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


@router.get("/stats")
async def get_stats(
    db: DbSessionDep,
    _user: AdminUserDep,
):
    total_consultations = (
        await db.execute(select(func.count()).select_from(Consultation))
    ).scalar_one()

    active_consultations = (
        await db.execute(
            select(func.count())
            .select_from(Consultation)
            .where(Consultation.status == "recording")
        )
    ).scalar_one()

    completed_consultations = (
        await db.execute(
            select(func.count())
            .select_from(Consultation)
            .where(Consultation.status == "completed")
        )
    ).scalar_one()

    return {
        "total_consultations": total_consultations,
        "active_consultations": active_consultations,
        "completed_consultations": completed_consultations,
    }


# --- Quality metrics endpoints ---


@router.get("/quality-metrics")
async def get_quality_metrics(
    db: DbSessionDep,
    _user: AdminUserDep,
    language: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    """Compare AI-generated SOAP (version 1) against finalized doctor version."""
    from app.db_models.soap_note import SOAPNote
    from app.db_models.soap_note_version import SOAPNoteVersion
    from app.models.quality_metrics import (
        QualityMetricsResponse,
        SectionEditMetrics,
    )

    # Finalized SOAP notes with version-1 (AI) snapshots
    query = (
        select(SOAPNote, SOAPNoteVersion, Consultation.language)
        .join(
            SOAPNoteVersion,
            (SOAPNoteVersion.soap_note_id == SOAPNote.id)
            & (SOAPNoteVersion.version == 1)
            & (SOAPNoteVersion.source == "ai_generated"),
        )
        .join(Consultation, Consultation.id == SOAPNote.consultation_id)
        .where(SOAPNote.is_draft.is_(False))
    )
    if language:
        query = query.where(Consultation.language == language)
    if date_from:
        query = query.where(Consultation.created_at >= date_from)
    if date_to:
        query = query.where(Consultation.created_at <= date_to)

    result = await db.execute(query)
    rows = result.all()

    # Count total finalized (with or without history)
    total_finalized = (
        await db.execute(
            select(func.count())
            .select_from(SOAPNote)
            .where(SOAPNote.is_draft.is_(False))
        )
    ).scalar_one()

    if not rows:
        return QualityMetricsResponse(
            overall_edit_rate=0.0,
            total_finalized=total_finalized,
            total_with_history=0,
            by_section=[],
            by_language={},
            period_start=date_from,
            period_end=date_to,
        )

    sections = ("subjective", "objective", "assessment", "plan")
    # Compute per-section edit distances
    by_language: dict[str, dict[str, list[float]]] = {}
    all_distances: dict[str, list[float]] = {s: [] for s in sections}
    any_edited_count = 0

    for soap, ai_version, lang in rows:
        has_any_edit = False
        lang_entry = by_language.setdefault(lang, {s: [] for s in sections})
        for section in sections:
            final_text = getattr(soap, section) or ""
            ai_text = getattr(ai_version, section) or ""
            ratio = difflib.SequenceMatcher(None, ai_text, final_text).ratio()
            dist = 1.0 - ratio
            if dist > 0.01:  # skip trivial whitespace changes
                has_any_edit = True
            all_distances[section].append(dist)
            lang_entry[section].append(dist)
        if has_any_edit:
            any_edited_count += 1

    def _build_section_metrics(
        distances: dict[str, list[float]],
    ) -> list[SectionEditMetrics]:
        metrics = []
        for section in sections:
            vals = distances[section]
            if not vals:
                continue
            edited_count = sum(1 for v in vals if v > 0.01)
            metrics.append(
                SectionEditMetrics(
                    section=section,
                    avg_edit_distance=sum(vals) / len(vals),
                    pct_edited=(edited_count / len(vals)) * 100,
                    total_compared=len(vals),
                )
            )
        return metrics

    return QualityMetricsResponse(
        overall_edit_rate=(any_edited_count / len(rows)) * 100 if rows else 0.0,
        total_finalized=total_finalized,
        total_with_history=len(rows),
        by_section=_build_section_metrics(all_distances),
        by_language={
            lang: _build_section_metrics(dists) for lang, dists in by_language.items()
        },
        period_start=date_from,
        period_end=date_to,
    )


@router.get("/flag-stats")
async def get_flag_stats(
    db: DbSessionDep,
    _user: AdminUserDep,
):
    """Return acceptance/dismissal rates for review flags."""
    from app.db_models.flag_feedback import FlagFeedback
    from app.db_models.soap_note import SOAPNote
    from app.models.quality_metrics import FlagStatsResponse, FlagTypeStats

    # Count total flags across finalized SOAP notes
    result = await db.execute(
        select(SOAPNote.review_flags).where(SOAPNote.is_draft.is_(False))
    )
    all_flags_json = result.scalars().all()

    total_flags = 0
    flags_by_type: dict[str, int] = {}
    flags_by_section: dict[str, int] = {}
    for flags_list in all_flags_json:
        if not isinstance(flags_list, list):
            continue
        total_flags += len(flags_list)
        for f in flags_list:
            if isinstance(f, dict):
                it = f.get("issue_type", "unknown")
                flags_by_type[it] = flags_by_type.get(it, 0) + 1
                sec = f.get("section", "unknown")
                flags_by_section[sec] = flags_by_section.get(sec, 0) + 1

    # Feedback counts
    feedback_rows = await db.execute(
        select(
            FlagFeedback.flag_issue_type,
            FlagFeedback.flag_section,
            FlagFeedback.action,
            func.count().label("cnt"),
        ).group_by(
            FlagFeedback.flag_issue_type,
            FlagFeedback.flag_section,
            FlagFeedback.action,
        )
    )
    feedback_data = feedback_rows.all()

    total_feedback = sum(row.cnt for row in feedback_data)

    # Aggregate by issue_type
    fb_by_type: dict[str, dict[str, int]] = {}
    fb_by_section: dict[str, dict[str, int]] = {}
    for row in feedback_data:
        fb_by_type.setdefault(row.flag_issue_type, {"accepted": 0, "dismissed": 0})
        fb_by_section.setdefault(row.flag_section, {"accepted": 0, "dismissed": 0})
        if row.action in ("accepted", "dismissed"):
            fb_by_type[row.flag_issue_type][row.action] += row.cnt
            fb_by_section[row.flag_section][row.action] += row.cnt

    by_issue_type = []
    for it, total in sorted(flags_by_type.items(), key=lambda x: -x[1]):
        fb = fb_by_type.get(it, {"accepted": 0, "dismissed": 0})
        responded = fb["accepted"] + fb["dismissed"]
        by_issue_type.append(
            FlagTypeStats(
                issue_type=it,
                total=total,
                accepted=fb["accepted"],
                dismissed=fb["dismissed"],
                acceptance_rate=(fb["accepted"] / responded * 100) if responded else 0,
            )
        )

    by_section = []
    for sec, total in sorted(flags_by_section.items(), key=lambda x: -x[1]):
        fb = fb_by_section.get(sec, {"accepted": 0, "dismissed": 0})
        responded = fb["accepted"] + fb["dismissed"]
        by_section.append(
            FlagTypeStats(
                issue_type=sec,
                total=total,
                accepted=fb["accepted"],
                dismissed=fb["dismissed"],
                acceptance_rate=(fb["accepted"] / responded * 100) if responded else 0,
            )
        )

    return FlagStatsResponse(
        total_flags=total_flags,
        total_feedback=total_feedback,
        by_issue_type=by_issue_type,
        by_section=by_section,
    )


@router.get("/export-training-data")
async def export_training_data(
    db: DbSessionDep,
    _user: AdminUserDep,
    language: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    """Stream JSONL training pairs: (transcript, AI SOAP, doctor SOAP)."""
    from app.db_models.soap_note import SOAPNote
    from app.db_models.soap_note_version import SOAPNoteVersion
    from app.db_models.transcript import Transcript

    # Finalized notes that have AI-generated baselines
    query = (
        select(
            SOAPNote,
            SOAPNoteVersion,
            Consultation.id.label("c_id"),
            Consultation.language,
        )
        .join(
            SOAPNoteVersion,
            (SOAPNoteVersion.soap_note_id == SOAPNote.id)
            & (SOAPNoteVersion.version == 1)
            & (SOAPNoteVersion.source == "ai_generated"),
        )
        .join(Consultation, Consultation.id == SOAPNote.consultation_id)
        .where(SOAPNote.is_draft.is_(False))
    )
    if language:
        query = query.where(Consultation.language == language)
    if date_from:
        query = query.where(Consultation.created_at >= date_from)
    if date_to:
        query = query.where(Consultation.created_at <= date_to)

    result = await db.execute(query)
    rows = result.all()

    async def _generate():
        for soap, ai_version, consultation_id, lang in rows:
            ai_soap = {
                "subjective": ai_version.subjective,
                "objective": ai_version.objective,
                "assessment": ai_version.assessment,
                "plan": ai_version.plan,
            }
            doctor_soap = {
                "subjective": soap.subjective,
                "objective": soap.objective,
                "assessment": soap.assessment,
                "plan": soap.plan,
            }
            # Skip if no corrections were made
            if ai_soap == doctor_soap:
                continue

            # Fetch medically relevant transcript
            t_result = await db.execute(
                select(Transcript.text)
                .where(
                    Transcript.consultation_id == consultation_id,
                    Transcript.is_medically_relevant.is_(True),
                )
                .order_by(Transcript.sequence_number)
            )
            transcript_parts = [row[0] for row in t_result.all()]
            transcript = "\n".join(transcript_parts)

            entry = {
                "consultation_id": str(consultation_id),
                "language": lang,
                "transcript": transcript,
                "ai_soap": ai_soap,
                "doctor_soap": doctor_soap,
            }
            yield json.dumps(entry, ensure_ascii=False) + "\n"

    return StreamingResponse(
        _generate(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": "attachment; filename=training-data.jsonl"},
    )


# --- User management endpoints ---


@router.get("/users", response_model=UserListResponse)
async def list_users(
    db: DbSessionDep,
    _user: AdminUserDep,
    offset: int = 0,
    limit: int = 20,
    search: str | None = None,
):
    query = select(User)
    if search:
        pattern = f"%{search}%"
        query = query.where(User.name.ilike(pattern) | User.email.ilike(pattern))

    total_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_query)).scalar_one()

    query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    body: CreateUserRequest,
    db: DbSessionDep,
    _user: AdminUserDep,
):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    body: UpdateUserRoleRequest,
    db: DbSessionDep,
    _user: AdminUserDep,
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.role = body.role
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/ban", response_model=UserResponse)
async def ban_user(
    user_id: str,
    body: BanUserRequest,
    db: DbSessionDep,
    _user: AdminUserDep,
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.banned = True
    user.ban_reason = body.ban_reason
    await db.commit()
    await db.refresh(user)

    # Revoke all active sessions for this user
    from sqlalchemy import update

    await db.execute(
        update(Session)
        .where(Session.user_id == user_id, Session.revoked == False)  # noqa: E712
        .values(revoked=True)
    )
    await db.commit()

    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/unban", response_model=UserResponse)
async def unban_user(
    user_id: str,
    db: DbSessionDep,
    _user: AdminUserDep,
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.banned = False
    user.ban_reason = None
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: DbSessionDep,
    current_user: AdminUserDep,
):
    if current_user["id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Delete sessions first
    from sqlalchemy import delete

    await db.execute(delete(Session).where(Session.user_id == user_id))
    await db.delete(user)
    await db.commit()


# --- Prompt template endpoints ---


@router.get("/prompts", response_model=PromptTemplateListResponse)
async def list_prompts(
    db: DbSessionDep,
    _user: AdminUserDep,
    offset: int = 0,
    limit: int = 20,
    active_only: bool = True,
):
    query = select(PromptTemplate)
    if active_only:
        query = query.where(PromptTemplate.is_active == True)  # noqa: E712
    total_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_query)).scalar_one()

    query = (
        query.order_by(PromptTemplate.slug, PromptTemplate.version.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return PromptTemplateListResponse(
        items=[PromptTemplateResponse.model_validate(p) for p in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/prompts/{slug}", response_model=PromptTemplateResponse)
async def get_prompt(
    slug: str,
    db: DbSessionDep,
    _user: AdminUserDep,
):
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.slug == slug,
            PromptTemplate.is_active == True,  # noqa: E712
        )
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found"
        )
    return PromptTemplateResponse.model_validate(prompt)


@router.get("/prompts/{slug}/versions", response_model=PromptVersionListResponse)
async def list_prompt_versions(
    slug: str,
    db: DbSessionDep,
    _user: AdminUserDep,
):
    result = await db.execute(
        select(PromptTemplate)
        .where(PromptTemplate.slug == slug)
        .order_by(PromptTemplate.version.desc())
    )
    versions = result.scalars().all()
    if not versions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found"
        )
    return PromptVersionListResponse(
        slug=slug,
        versions=[PromptTemplateResponse.model_validate(v) for v in versions],
    )


@router.put("/prompts/{slug}", response_model=PromptTemplateResponse)
async def update_prompt(
    slug: str,
    body: PromptTemplateUpdate,
    db: DbSessionDep,
    user: AdminUserDep,
    request: Request,
):
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.slug == slug,
            PromptTemplate.is_active == True,  # noqa: E712
        )
    )
    current = result.scalar_one_or_none()
    if not current:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found"
        )

    current.is_active = False

    new_prompt = PromptTemplate(
        slug=slug,
        version=current.version + 1,
        is_active=True,
        title=body.title or current.title,
        description=(
            body.description if body.description is not None else current.description
        ),
        content=body.content,
        variables=(body.variables if body.variables is not None else current.variables),
        created_by=user["id"],
    )
    db.add(new_prompt)
    await db.commit()
    await db.refresh(new_prompt)

    from app.database import async_session_factory

    registry = request.app.state.prompt_registry
    await registry.refresh(async_session_factory, slug=slug)

    return PromptTemplateResponse.model_validate(new_prompt)


@router.post(
    "/prompts/{slug}/activate/{version}",
    response_model=PromptTemplateResponse,
)
async def activate_prompt_version(
    slug: str,
    version: int,
    db: DbSessionDep,
    _user: AdminUserDep,
    request: Request,
):
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.slug == slug,
            PromptTemplate.version == version,
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Version not found"
        )

    await db.execute(
        update(PromptTemplate)
        .where(PromptTemplate.slug == slug)
        .values(is_active=False)
    )
    target.is_active = True
    await db.commit()
    await db.refresh(target)

    from app.database import async_session_factory

    registry = request.app.state.prompt_registry
    await registry.refresh(async_session_factory, slug=slug)

    return PromptTemplateResponse.model_validate(target)
