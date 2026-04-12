from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "TOCKY_"}

    app_name: str = "Tocky API"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://tocky:tocky@localhost:5432/tocky"

    # Authentication
    auth_secret: str = "change-me-to-a-random-secret"

    # Alibaba Cloud DashScope (Qwen2.5-Omni)
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model_name: str = "qwen2.5-omni-7b"

    # Alibaba Cloud OSS
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_bucket_name: str = "tocky-audio"
    oss_endpoint: str = ""

    # Audio processing
    audio_buffer_seconds: float = 5.0
    soap_update_interval_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
