from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "TOCKY_"}

    app_name: str = "Tocky API"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://tocky:tocky@localhost:5432/tocky"


@lru_cache
def get_settings() -> Settings:
    return Settings()
