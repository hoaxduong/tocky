from fastapi import APIRouter

from app.dependencies import SettingsDep
from app.models.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def check_health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version="0.1.0",
    )
