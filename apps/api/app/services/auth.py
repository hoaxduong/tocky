from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

security = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.auth_secret,
            algorithms=["HS256"],
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return {
        "id": payload.get("sub"),
        "email": payload.get("email"),
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
