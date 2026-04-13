from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = {
        "env_prefix": "TOCKY_",
        "env_file": str(_ENV_FILE) if _ENV_FILE.exists() else None,
        "extra": "ignore",
    }

    app_name: str = "Tocky API"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://tocky:tocky@localhost:5432/tocky"

    # Authentication (ES256 ECDSA keys)
    jwt_private_key: str = ""  # PEM-encoded EC private key
    jwt_public_key: str = ""  # PEM-encoded EC public key

    # Alibaba Cloud DashScope
    dashscope_api_key: str = ""
    # Regional: dashscope.aliyuncs.com (Beijing),
    # dashscope-intl.aliyuncs.com (SG), dashscope-us.aliyuncs.com (VA)
    dashscope_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    qwen_model_name: str = "qwen2.5-omni-7b"  # fallback for all workloads

    # Per-workload model overrides (leave empty to use qwen_model_name for all)
    qwen_transcription_model: str = ""
    qwen_classification_model: str = ""
    qwen_soap_model: str = ""
    qwen_extraction_model: str = ""

    # Alibaba Cloud OSS
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_bucket_name: str = "tocky-audio"
    oss_endpoint: str = ""

    # Audio processing
    audio_buffer_seconds: float = 5.0
    soap_update_interval_seconds: float = 30.0

    # DashScope Streaming ASR (real-time transcription via WebSocket)
    dashscope_ws_base_url: str = "wss://dashscope-intl.aliyuncs.com"
    qwen_streaming_asr_model: str = "qwen3-asr-flash-realtime"

    # Server VAD turn detection tuning
    vad_threshold: float = 0.5
    vad_silence_duration_ms: int = 1200
    vad_prefix_padding_ms: int = 300

    # Sandbox mode (bypass DashScope with fake AI responses)
    sandbox_ai: bool = False
    sandbox_ai_latency: float = 0.2


@lru_cache
def get_settings() -> Settings:
    return Settings()
