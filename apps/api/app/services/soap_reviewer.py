import json
import re


class SOAPReviewer:
    ISSUE_TYPES = (
        "symptom_diagnosis_mismatch",
        "ambiguous_term",
        "translation_uncertainty",
        "missing_information",
    )

    SYSTEM_PROMPT = (
        "You are a clinical QA reviewer. You receive a medical consultation "
        "transcript and a draft SOAP note. Identify issues that the physician "
        "should verify before finalizing.\n\n"
        "Issue types:\n"
        "- symptom_diagnosis_mismatch: the assessment does not match the "
        "symptoms present in the transcript, or the symptom combination is "
        "clinically implausible for the stated condition.\n"
        "- ambiguous_term: a term in the SOAP has multiple plausible medical "
        "meanings that change clinical interpretation.\n"
        "- translation_uncertainty: a term was translated from the source "
        "language and has more than one valid medical rendering.\n"
        "- missing_information: the SOAP omits a clinically relevant fact "
        "clearly stated in the transcript.\n\n"
        "Rules:\n"
        "1. Every flag MUST quote the exact span from the transcript OR the "
        "SOAP note that grounds the concern. Do not invent quotes.\n"
        "2. Flag only concerns a physician would actually want surfaced. "
        "Skip stylistic preferences.\n"
        "3. Return confidence as one of: low, medium, high.\n"
        '4. If nothing is worth flagging, return {"flags": []}.\n\n'
        "Respond with a single valid JSON object in this shape:\n"
        '{"flags": ['
        '{"section": "subjective|objective|assessment|plan", '
        '"quoted_span": "<text copied verbatim>", '
        '"issue_type": "<one of the issue types>", '
        '"suggestion": "<what the physician should verify or consider>", '
        '"confidence": "low|medium|high"}'
        "]}\n"
        "Output ONLY the JSON. No prose, no markdown fence."
    )

    def build_review_prompt(
        self,
        transcript: str,
        soap: dict[str, str],
        language: str,
    ) -> list[dict]:
        soap_block = (
            f"## Subjective\n{soap.get('subjective', '')}\n\n"
            f"## Objective\n{soap.get('objective', '')}\n\n"
            f"## Assessment\n{soap.get('assessment', '')}\n\n"
            f"## Plan\n{soap.get('plan', '')}"
        )
        user_content = (
            f"Source language: {language}\n\n"
            f"=== TRANSCRIPT ===\n{transcript}\n\n"
            f"=== DRAFT SOAP NOTE ===\n{soap_block}"
        )
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    def parse_review_response(self, response_text: str) -> list[dict]:
        text = response_text.strip()
        fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []

        raw_flags = data.get("flags") if isinstance(data, dict) else None
        if not isinstance(raw_flags, list):
            return []

        valid_sections = {"subjective", "objective", "assessment", "plan"}
        valid_confidence = {"low", "medium", "high"}
        cleaned: list[dict] = []
        for item in raw_flags:
            if not isinstance(item, dict):
                continue
            section = str(item.get("section", "")).lower().strip()
            issue_type = str(item.get("issue_type", "")).strip()
            quoted = str(item.get("quoted_span", "")).strip()
            suggestion = str(item.get("suggestion", "")).strip()
            confidence = str(item.get("confidence", "")).lower().strip()
            if section not in valid_sections:
                continue
            if issue_type not in self.ISSUE_TYPES:
                continue
            if not quoted or not suggestion:
                continue
            if confidence not in valid_confidence:
                confidence = "medium"
            cleaned.append(
                {
                    "section": section,
                    "quoted_span": quoted,
                    "issue_type": issue_type,
                    "suggestion": suggestion,
                    "confidence": confidence,
                }
            )
        return cleaned
