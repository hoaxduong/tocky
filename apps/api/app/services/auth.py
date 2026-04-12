import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

import bcrypt
import jwt
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
ISSUER = "tocky"

security = HTTPBearer(auto_error=False)


def _get_private_key():
    settings = get_settings()
    return load_pem_private_key(settings.jwt_private_key.encode(), password=None)


def _get_public_key():
    settings = get_settings()
    return settings.jwt_public_key


# --- Password hashing ---


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


# --- Token utilities ---


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: str, email: str, role: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "iss": ISSUER,
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, _get_private_key(), algorithm="ES256")


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_public_key,
            algorithms=["ES256"],
            issuer=ISSUER,
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
        ) from e


# --- FastAPI dependencies ---


def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security)
    ] = None,
    tocky_access: Annotated[str | None, Cookie()] = None,
) -> dict:
    token = None
    if credentials:
        token = credentials.credentials
    elif tocky_access:
        token = tocky_access

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_access_token(token)
    return {
        "id": payload["sub"],
        "email": payload["email"],
        "role": payload.get("role", "doctor"),
    }


def require_role(role: str):
    def _check(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required",
            )
        return user

    return _check


CurrentUserDep = Annotated[dict, Depends(get_current_user)]
AdminUserDep = Annotated[dict, Depends(require_role("admin"))]
DoctorUserDep = Annotated[dict, Depends(require_role("doctor"))]
