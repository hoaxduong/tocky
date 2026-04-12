from __future__ import annotations

import base64
import json
import logging
import struct
from typing import TYPE_CHECKING

import httpx

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.services.prompt_registry import PromptRegistry

# Language code mapping for ASR models (ISO codes)
_ASR_LANGUAGE_MAP = {
    "vi": "vi",
    "ar-eg": "ar",
    "ar-gulf": "ar",
    "en": "en",
}


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
    """Wrap raw 16-bit mono PCM data in a WAV header."""
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = len(pcm_bytes)

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,  # chunk size
        1,  # PCM format
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + pcm_bytes


class DashScopeClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        transcription_model: str,
        classification_model: str,
        soap_model: str,
        extraction_model: str,
        prompt_registry: PromptRegistry,
    ):
        self.transcription_model = transcription_model
        self.classification_model = classification_model
        self.soap_model = soap_model
        self.extraction_model = extraction_model
        self.prompts = prompt_registry
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
        )

    async def transcribe_audio(self, audio_bytes: bytes, language: str) -> str:
        logger.debug(
            "transcribe_audio: model=%s, language=%s, audio_size=%d bytes",
            self.transcription_model,
            language,
            len(audio_bytes),
        )
        if self.transcription_model.startswith("qwen3-asr"):
            return await self._transcribe_asr(audio_bytes, language)
        return await self._transcribe_omni(audio_bytes, language)

    async def _transcribe_asr(self, audio_bytes: bytes, language: str) -> str:
        wav_bytes = _pcm_to_wav(audio_bytes)
        audio_b64 = base64.b64encode(wav_bytes).decode()
        data_uri = f"data:audio/wav;base64,{audio_b64}"

        payload: dict = {
            "model": self.transcription_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {"data": data_uri},
                        },
                    ],
                },
            ],
        }

        if language != "auto":
            asr_lang = _ASR_LANGUAGE_MAP.get(language)
            if asr_lang:
                payload["asr_options"] = {"language": asr_lang}

        logger.debug("ASR request: model=%s", payload["model"])
        response = await self.client.post("/chat/completions", json=payload)
        logger.debug("ASR response: status=%d", response.status_code)
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        logger.debug("ASR result: %d chars — %s", len(text), text[:100])
        return text

    async def _transcribe_omni(self, audio_bytes: bytes, language: str) -> str:
        audio_b64 = base64.b64encode(audio_bytes).decode()

        if language == "auto":
            lang_instruction = (
                "Auto-detect the language of the audio and transcribe it."
            )
        else:
            language_hint = {
                "vi": "Vietnamese",
                "ar-eg": "Egyptian Arabic",
                "ar-gulf": "Gulf Arabic",
                "en": "English",
            }.get(language, "English")
            lang_instruction = f"Transcribe the audio in {language_hint}."

        system_content = self.prompts.get(
            "transcription_omni", language_instruction=lang_instruction
        )

        logger.debug(
            "Omni transcription: model=%s, prompt=%s",
            self.transcription_model,
            system_content[:100],
        )
        response = await self.client.post(
            "/chat/completions",
            json={
                "model": self.transcription_model,
                "messages": [
                    {"role": "system", "content": system_content},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": audio_b64,
                                    "format": "pcm",
                                    "sample_rate": 16000,
                                },
                            },
                        ],
                    },
                ],
            },
        )
        logger.debug("Omni response: status=%d", response.status_code)
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        logger.debug("Omni result: %d chars — %s", len(text), text[:100])
        return text

    async def classify_relevance(self, text: str, language: str) -> bool:
        import time

        t0 = time.monotonic()
        response = await self.client.post(
            "/chat/completions",
            json={
                "model": self.classification_model,
                "messages": [
                    {
                        "role": "system",
                        "content": self.prompts.get("classification"),
                    },
                    {"role": "user", "content": text},
                ],
                "max_tokens": 10,
            },
        )
        elapsed = time.monotonic() - t0
        logger.debug(
            "classify_relevance: status=%d, %.1fs",
            response.status_code,
            elapsed,
        )
        response.raise_for_status()
        data = response.json()
        answer = data["choices"][0]["message"]["content"].strip().upper()
        return "RELEVANT" in answer

    async def generate_soap(
        self, transcript_text: str, language: str
    ) -> dict[str, str]:
        from app.services.soap_generator import SOAPGenerator

        generator = SOAPGenerator(self.prompts)
        messages = generator.build_soap_prompt(transcript_text, language)

        response = await self.client.post(
            "/chat/completions",
            json={
                "model": self.soap_model,
                "messages": messages,
                "max_tokens": 2000,
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return generator.parse_soap_response(content)

    async def extract_medical_entities(self, text: str, language: str) -> dict:
        response = await self.client.post(
            "/chat/completions",
            json={
                "model": self.extraction_model,
                "messages": [
                    {
                        "role": "system",
                        "content": self.prompts.get("entity_extraction"),
                    },
                    {"role": "user", "content": text},
                ],
                "max_tokens": 1000,
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}

    async def detect_language(self, text: str) -> str:
        """Detect language from transcript text. Returns a language code."""
        response = await self.client.post(
            "/chat/completions",
            json={
                "model": self.classification_model,
                "messages": [
                    {
                        "role": "system",
                        "content": self.prompts.get("language_detection"),
                    },
                    {"role": "user", "content": text[:2000]},
                ],
                "max_tokens": 10,
            },
        )
        response.raise_for_status()
        data = response.json()
        code = data["choices"][0]["message"]["content"].strip().lower()
        valid_codes = {"vi", "ar-eg", "ar-gulf", "en"}
        return code if code in valid_codes else "en"

    async def extract_consultation_metadata(
        self, transcript_text: str
    ) -> dict[str, str]:
        """Extract a short title and patient identifier from transcript."""
        response = await self.client.post(
            "/chat/completions",
            json={
                "model": self.classification_model,
                "messages": [
                    {
                        "role": "system",
                        "content": self.prompts.get("metadata_extraction"),
                    },
                    {"role": "user", "content": transcript_text[:4000]},
                ],
                "max_tokens": 200,
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(content)
            return {
                "title": str(parsed.get("title", ""))[:255],
                "patient_identifier": (
                    str(parsed["patient_identifier"])[:100]
                    if parsed.get("patient_identifier")
                    else None
                ),
            }
        except (json.JSONDecodeError, TypeError):
            return {"title": "", "patient_identifier": None}

    async def close(self) -> None:
        await self.client.aclose()
