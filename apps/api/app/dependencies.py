from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db_session
from app.services.auth import (
    AdminUserDep,
    CurrentUserDep,
    DoctorUserDep,
)

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]

# Re-export auth deps for convenience
__all__ = [
    "SettingsDep",
    "DbSessionDep",
    "CurrentUserDep",
    "AdminUserDep",
    "DoctorUserDep",
]
