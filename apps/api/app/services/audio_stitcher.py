import asyncio
import io
import uuid
import wave

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models.audio_segment import AudioSegment
from app.services.oss_client import OSSClient


class AudioStitcher:
    def __init__(self, oss: OSSClient):
        self.oss = oss

    async def stitch_consultation(
        self,
        db: AsyncSession,
        consultation_id: uuid.UUID,
    ) -> tuple[str, int] | None:
        result = await db.execute(
            select(AudioSegment)
            .where(AudioSegment.consultation_id == consultation_id)
            .order_by(AudioSegment.sequence_number.asc())
        )
        segments = result.scalars().all()
        if not segments:
            return None

        sample_rate = segments[0].sample_rate
        pcm_parts = await asyncio.gather(
            *[
                asyncio.to_thread(self.oss.download_object, seg.oss_key)
                for seg in segments
            ]
        )
        pcm_data = b"".join(pcm_parts)
        duration_ms = sum(seg.duration_ms for seg in segments)

        wav_bytes = _wrap_pcm_as_wav(pcm_data, sample_rate)
        oss_key = await asyncio.to_thread(
            self.oss.upload_full_audio, consultation_id, wav_bytes, "wav"
        )
        return oss_key, duration_ms


def _wrap_pcm_as_wav(pcm_data: bytes, sample_rate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_data)
    return buffer.getvalue()
