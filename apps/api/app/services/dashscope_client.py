import base64
import json
import struct

import httpx

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
    ):
        self.transcription_model = transcription_model
        self.classification_model = classification_model
        self.soap_model = soap_model
        self.extraction_model = extraction_model
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
        )

    async def transcribe_audio(self, audio_bytes: bytes, language: str) -> str:
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

        asr_lang = _ASR_LANGUAGE_MAP.get(language)
        if asr_lang:
            payload["asr_options"] = {"language": asr_lang}

        response = await self.client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _transcribe_omni(self, audio_bytes: bytes, language: str) -> str:
        audio_b64 = base64.b64encode(audio_bytes).decode()
        language_hint = {
            "vi": "Vietnamese",
            "ar-eg": "Egyptian Arabic",
            "ar-gulf": "Gulf Arabic",
            "en": "English",
        }.get(language, "English")

        response = await self.client.post(
            "/chat/completions",
            json={
                "model": self.transcription_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            f"You are a medical transcription assistant. "
                            f"Transcribe the audio in {language_hint}. "
                            f"Output only the transcription text, nothing else."
                        ),
                    },
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
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def classify_relevance(self, text: str, language: str) -> bool:
        response = await self.client.post(
            "/chat/completions",
            json={
                "model": self.classification_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You classify medical consultation transcript segments. "
                            "Reply with exactly one word: RELEVANT or IRRELEVANT. "
                            "RELEVANT = contains medical information (symptoms, "
                            "diagnoses, medications, procedures, vitals, history). "
                            "IRRELEVANT = small talk, greetings, weather, etc."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                "max_tokens": 10,
            },
        )
        response.raise_for_status()
        data = response.json()
        answer = data["choices"][0]["message"]["content"].strip().upper()
        return "RELEVANT" in answer

    async def generate_soap(
        self, transcript_text: str, language: str
    ) -> dict[str, str]:
        from app.services.soap_generator import SOAPGenerator

        generator = SOAPGenerator()
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
                        "content": (
                            "Extract medical entities from the consultation "
                            "transcript. Output valid JSON with these categories: "
                            "symptoms, diagnoses, medications, procedures, vitals, "
                            "allergies. Each category is an array of strings. "
                            "Output only the JSON object, no other text."
                        ),
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

    async def close(self) -> None:
        await self.client.aclose()
