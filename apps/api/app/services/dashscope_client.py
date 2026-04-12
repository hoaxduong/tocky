import base64
import json

import httpx


class DashScopeClient:
    def __init__(self, base_url: str, api_key: str, model_name: str):
        self.model_name = model_name
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
        )

    async def transcribe_audio(self, audio_bytes: bytes, language: str) -> str:
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
                "model": self.model_name,
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
                "model": self.model_name,
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
                "model": self.model_name,
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
                "model": self.model_name,
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
