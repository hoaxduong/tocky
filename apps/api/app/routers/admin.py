from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.db_models.consultation import Consultation
from app.db_models.session import Session
from app.db_models.user import User
from app.dependencies import AdminUserDep, DbSessionDep
from app.models.consultation import ConsultationListResponse, ConsultationResponse
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
        query = query.where(
            User.name.ilike(pattern) | User.email.ilike(pattern)
        )

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


@router.delete(
    "/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
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
