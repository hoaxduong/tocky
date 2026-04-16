import json
import re

from pydantic import ValidationError

from app.models.review_flag import (
    ISSUE_SEVERITY_DEFAULTS,
    ReviewFlag,
    ReviewFlagSource,
    ReviewIssueType,
    ReviewSeverity,
)


class SOAPReviewer:
    ISSUE_TYPES = tuple(e.value for e in ReviewIssueType)

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
        "clearly stated in the transcript.\n"
        "- dosage_concern: a medication dosage mentioned seems outside typical "
        "ranges, or the dosage was unclear in the transcript but appears "
        "definitive in the SOAP.\n"
        "- contraindication: a prescribed treatment or medication may conflict "
        "with a known condition, allergy, or current medication visible in the "
        "transcript or patient history.\n"
        "- temporal_inconsistency: the timeline of symptoms or events in the "
        "SOAP does not match what was stated in the transcript.\n"
        "- vital_sign_mismatch: vital signs or lab values in the SOAP do not "
        "match what was stated or recorded in the transcript.\n\n"
        "Severity levels (choose one per flag):\n"
        "- critical: potential patient safety issue (e.g. wrong dosage, "
        "contraindication, dangerous vital sign error).\n"
        "- warning: clinical accuracy concern that may affect the care plan.\n"
        "- info: worth noting but low risk (e.g. ambiguous wording, minor "
        "translation nuance).\n\n"
        "Rules:\n"
        "1. Every flag MUST quote the exact span from the transcript OR the "
        "SOAP note that grounds the concern. Do not invent quotes.\n"
        "2. Flag only concerns a physician would actually want surfaced. "
        "Skip stylistic preferences.\n"
        "3. Return confidence as one of: low, medium, high.\n"
        '4. If nothing is worth flagging, return {"flags": []}.\n\n'
        "Respond with a single valid JSON object in this shape:\n"
        '{"flags": [{"section": "subjective|objective|assessment|plan", '
        '"quoted_span": "<text copied verbatim>", '
        '"issue_type": "<one of the issue types above>", '
        '"suggestion": "<what the physician should verify or consider>", '
        '"confidence": "low|medium|high", '
        '"severity": "info|warning|critical"'
        "}]}\n\n"
        "Examples:\n\n"
        'Example 1 — flags found:\n'
        '{"flags": ['
        '{"section": "assessment", '
        '"quoted_span": "Patient diagnosed with hypertension", '
        '"issue_type": "symptom_diagnosis_mismatch", '
        '"suggestion": "Transcript mentions dizziness and headaches but no '
        'blood pressure reading was discussed. Verify BP was measured.", '
        '"confidence": "high", "severity": "warning"}, '
        '{"section": "plan", '
        '"quoted_span": "Metformin 500mg twice daily", '
        '"issue_type": "contraindication", '
        '"suggestion": "Patient mentioned current kidney issues in transcript. '
        'Verify renal function before prescribing metformin.", '
        '"confidence": "medium", "severity": "critical"}'
        "]}\n\n"
        'Example 2 — no flags:\n'
        '{"flags": []}\n\n'
        "Output ONLY the JSON. No prose, no markdown fence."
    )

    def build_review_prompt(
        self,
        transcript: str,
        soap: dict[str, str],
        language: str,
        patient_history: str = "",
    ) -> list[dict]:
        soap_block = (
            f"## Subjective\n{soap.get('subjective', '')}\n\n"
            f"## Objective\n{soap.get('objective', '')}\n\n"
            f"## Assessment\n{soap.get('assessment', '')}\n\n"
            f"## Plan\n{soap.get('plan', '')}"
        )
        parts = [f"Source language: {language}\n"]
        if patient_history:
            parts.append(
                f"=== PATIENT HISTORY ===\n{patient_history}\n"
            )
        parts.append(f"=== TRANSCRIPT ===\n{transcript}\n")
        parts.append(f"=== DRAFT SOAP NOTE ===\n{soap_block}")
        user_content = "\n".join(parts)
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    def _validate_flags(self, raw_flags: list) -> list[dict]:
        cleaned: list[dict] = []
        for item in raw_flags:
            if not isinstance(item, dict):
                continue
            # Normalize confidence default before validation
            confidence = str(item.get("confidence", "")).lower().strip()
            if confidence not in {"low", "medium", "high"}:
                item["confidence"] = "medium"
            # Derive severity from issue_type if not provided by the LLM
            if "severity" not in item or item["severity"] not in {
                "info",
                "warning",
                "critical",
            }:
                issue_type_str = str(item.get("issue_type", ""))
                try:
                    issue_enum = ReviewIssueType(issue_type_str)
                    item["severity"] = ISSUE_SEVERITY_DEFAULTS.get(
                        issue_enum, ReviewSeverity.warning
                    )
                except ValueError:
                    item["severity"] = "warning"
            item["source"] = ReviewFlagSource.ai_review
            try:
                flag = ReviewFlag.model_validate(item)
                cleaned.append(flag.model_dump())
            except ValidationError:
                continue
        return cleaned

    def parse_review_data(self, data: dict | list) -> list[dict]:
        """Parse already-decoded JSON data into validated flags."""
        raw_flags = data.get("flags") if isinstance(data, dict) else None
        if not isinstance(raw_flags, list):
            return []
        return self._validate_flags(raw_flags)

    def parse_review_response(self, response_text: str) -> list[dict]:
        text = response_text.strip()
        fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []

        return self.parse_review_data(data)
