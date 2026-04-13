"""Filesystem-based drop-in replacement for OSSClient.

Stores files under a local directory and generates URLs served by a
FastAPI static route.  Designed for local development only.
"""

import uuid
from pathlib import Path


class LocalStorageClient:
    def __init__(self, storage_dir: str | Path, base_url: str):
        self.root = Path(storage_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url.rstrip("/")

    def _write(self, key: str, data: bytes) -> None:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def upload_audio(
        self,
        consultation_id: uuid.UUID,
        sequence: int,
        audio_bytes: bytes,
    ) -> str:
        oss_key = f"audio/{consultation_id}/{sequence:06d}.pcm"
        self._write(oss_key, audio_bytes)
        return oss_key

    def get_audio_url(self, oss_key: str, expires: int = 3600) -> str:
        return f"{self.base_url}/storage/{oss_key}"

    def download_object(self, oss_key: str) -> bytes:
        path = self.root / oss_key
        return path.read_bytes()

    def upload_full_audio(
        self,
        consultation_id: uuid.UUID,
        audio_bytes: bytes,
        extension: str = "wav",
    ) -> str:
        oss_key = f"audio/{consultation_id}/full.{extension}"
        self._write(oss_key, audio_bytes)
        return oss_key

    def upload_pcm(
        self,
        consultation_id: uuid.UUID,
        pcm_bytes: bytes,
    ) -> str:
        oss_key = f"audio/{consultation_id}/source.pcm"
        self._write(oss_key, pcm_bytes)
        return oss_key
