from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select

from app.db_models.session import Session
from app.db_models.user import User
from app.dependencies import DbSessionDep
from app.models.user import (
    SessionResponse,
    SignInRequest,
    SignUpRequest,
    UserResponse,
)
from app.services.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    CurrentUserDep,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_SECURE = False  # Set True in production (HTTPS)
COOKIE_SAMESITE = "lax"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(
        key="tocky_access",
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="tocky_refresh",
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth/refresh",
    )


def _clear_auth_cookies(response: Response):
    response.delete_cookie("tocky_access", path="/")
    response.delete_cookie("tocky_refresh", path="/api/v1/auth/refresh")


async def _create_session(
    db: DbSessionDep,
    user: User,
    request: Request,
    response: Response,
):
    access_token = create_access_token(user.id, user.email, user.role)
    refresh_token = create_refresh_token()

    session = Session(
        id=access_token.split(".")[-1][:36].replace("-", "")[:36],
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        ip_address=(request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent", "")[:512],
    )
    db.add(session)
    await db.commit()

    _set_auth_cookies(response, access_token, refresh_token)
    return UserResponse.model_validate(user)


@router.post("/sign-up", response_model=SessionResponse)
async def sign_up(
    body: SignUpRequest,
    db: DbSessionDep,
    request: Request,
    response: Response,
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
    )
    db.add(user)
    await db.flush()

    user_resp = await _create_session(db, user, request, response)
    return SessionResponse(user=user_resp)


@router.post("/sign-in", response_model=SessionResponse)
async def sign_in(
    body: SignInRequest,
    db: DbSessionDep,
    request: Request,
    response: Response,
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is banned",
        )

    user_resp = await _create_session(db, user, request, response)
    return SessionResponse(user=user_resp)


@router.post("/sign-out", status_code=status.HTTP_204_NO_CONTENT)
async def sign_out(
    request: Request,
    db: DbSessionDep,
    response: Response,
):
    refresh_token = request.cookies.get("tocky_refresh")
    if refresh_token:
        token_hash = hash_token(refresh_token)
        result = await db.execute(
            select(Session).where(
                Session.token_hash == token_hash,
                Session.revoked == False,  # noqa: E712
            )
        )
        session = result.scalar_one_or_none()
        if session:
            session.revoked = True
            await db.commit()

    _clear_auth_cookies(response)


@router.post("/refresh", response_model=SessionResponse)
async def refresh(
    request: Request,
    db: DbSessionDep,
    response: Response,
):
    refresh_token = request.cookies.get("tocky_refresh")
    if not refresh_token:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )

    token_hash = hash_token(refresh_token)
    result = await db.execute(select(Session).where(Session.token_hash == token_hash))
    session = result.scalar_one_or_none()

    if not session:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Token reuse detection: if already revoked, revoke ALL user sessions
    if session.revoked:
        await db.execute(
            select(Session)
            .where(Session.user_id == session.user_id)
            .execution_options(synchronize_session="fetch")
        )
        # Revoke all sessions for this user
        from sqlalchemy import update

        await db.execute(
            update(Session)
            .where(Session.user_id == session.user_id)
            .values(revoked=True)
        )
        await db.commit()
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token reuse detected — all sessions revoked",
        )

    if session.expires_at < datetime.now(UTC):
        session.revoked = True
        await db.commit()
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )

    # Revoke old session
    session.revoked = True

    # Load user
    user_result = await db.execute(select(User).where(User.id == session.user_id))
    user = user_result.scalar_one_or_none()
    if not user or user.banned:
        await db.commit()
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or banned",
        )

    # Issue new tokens
    user_resp = await _create_session(db, user, request, response)
    return SessionResponse(user=user_resp)


@router.get("/session", response_model=SessionResponse)
async def get_session(
    user: CurrentUserDep,
    db: DbSessionDep,
):
    result = await db.execute(select(User).where(User.id == user["id"]))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return SessionResponse(user=UserResponse.model_validate(db_user))
