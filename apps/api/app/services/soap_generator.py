import re


class SOAPGenerator:
    SYSTEM_PROMPTS = {
        "vi": (
            "Bạn là trợ lý lâm sàng chuyên nghiệp. Từ bản ghi tư vấn y tế, "
            "hãy tạo ghi chú SOAP bằng tiếng Việt. Sử dụng thuật ngữ y khoa "
            "chuẩn và nhận diện các thực thể y tế theo VietMed: "
            "triệu chứng, bệnh, thuốc, thủ thuật, chỉ số sinh tồn, dị ứng.\n\n"
            "Định dạng đầu ra:\n"
            "## Subjective\n<nội dung>\n\n"
            "## Objective\n<nội dung>\n\n"
            "## Assessment\n<nội dung>\n\n"
            "## Plan\n<nội dung>"
        ),
        "ar-eg": (
            "أنت مساعد سريري محترف. من نص الاستشارة الطبية، أنشئ ملاحظة SOAP "
            "باللهجة المصرية مع المصطلحات الطبية القياسية.\n\n"
            "التنسيق:\n"
            "## Subjective\n<المحتوى>\n\n"
            "## Objective\n<المحتوى>\n\n"
            "## Assessment\n<المحتوى>\n\n"
            "## Plan\n<المحتوى>"
        ),
        "ar-gulf": (
            "أنت مساعد سريري محترف. من نص الاستشارة الطبية، أنشئ ملاحظة SOAP "
            "باللهجة الخليجية مع المصطلحات الطبية القياسية.\n\n"
            "التنسيق:\n"
            "## Subjective\n<المحتوى>\n\n"
            "## Objective\n<المحتوى>\n\n"
            "## Assessment\n<المحتوى>\n\n"
            "## Plan\n<المحتوى>"
        ),
        "en": (
            "You are a professional clinical assistant. From the medical "
            "consultation transcript, generate a SOAP note using standard "
            "medical terminology.\n\n"
            "Format:\n"
            "## Subjective\n<content>\n\n"
            "## Objective\n<content>\n\n"
            "## Assessment\n<content>\n\n"
            "## Plan\n<content>"
        ),
    }

    def build_soap_prompt(self, transcript: str, language: str) -> list[dict]:
        system_prompt = self.SYSTEM_PROMPTS.get(language, self.SYSTEM_PROMPTS["en"])
        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Consultation transcript:\n\n{transcript}",
            },
        ]

    def parse_soap_response(self, response_text: str) -> dict[str, str]:
        sections = {
            "subjective": "",
            "objective": "",
            "assessment": "",
            "plan": "",
        }

        heading = r"Subjective|Objective|Assessment|Plan"
        pattern = (
            rf"##\s*({heading})\s*\n(.*?)"
            rf"(?=##\s*(?:{heading})|\Z)"
        )
        matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)

        for heading, content in matches:
            key = heading.strip().lower()
            if key in sections:
                sections[key] = content.strip()

        return sections

    def build_relevance_prompt(self, text: str, language: str) -> list[dict]:
        return [
            {
                "role": "system",
                "content": (
                    "You classify medical consultation transcript segments. "
                    "Reply with exactly one word: RELEVANT or IRRELEVANT. "
                    "RELEVANT = contains medical information. "
                    "IRRELEVANT = small talk, greetings, non-medical content."
                ),
            },
            {"role": "user", "content": text},
        ]
