import uuid
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class ReviewIssueType(StrEnum):
    symptom_diagnosis_mismatch = "symptom_diagnosis_mismatch"
    ambiguous_term = "ambiguous_term"
    translation_uncertainty = "translation_uncertainty"
    missing_information = "missing_information"
    low_confidence_section = "low_confidence_section"
    dosage_concern = "dosage_concern"
    contraindication = "contraindication"
    temporal_inconsistency = "temporal_inconsistency"
    vital_sign_mismatch = "vital_sign_mismatch"


class ReviewSeverity(StrEnum):
    info = "info"
    warning = "warning"
    critical = "critical"


class ReviewFlagSource(StrEnum):
    ai_confidence = "ai_confidence"
    ai_review = "ai_review"


class ReviewConfidence(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class SOAPSectionName(StrEnum):
    subjective = "subjective"
    objective = "objective"
    assessment = "assessment"
    plan = "plan"


# Default severity per issue type
ISSUE_SEVERITY_DEFAULTS: dict[ReviewIssueType, ReviewSeverity] = {
    ReviewIssueType.dosage_concern: ReviewSeverity.critical,
    ReviewIssueType.contraindication: ReviewSeverity.critical,
    ReviewIssueType.symptom_diagnosis_mismatch: ReviewSeverity.warning,
    ReviewIssueType.vital_sign_mismatch: ReviewSeverity.warning,
    ReviewIssueType.missing_information: ReviewSeverity.warning,
    ReviewIssueType.ambiguous_term: ReviewSeverity.info,
    ReviewIssueType.translation_uncertainty: ReviewSeverity.info,
    ReviewIssueType.low_confidence_section: ReviewSeverity.info,
    ReviewIssueType.temporal_inconsistency: ReviewSeverity.warning,
}


class ReviewFlag(BaseModel):
    section: SOAPSectionName
    quoted_span: str = Field(min_length=1)
    issue_type: ReviewIssueType
    suggestion: str = Field(min_length=1)
    confidence: ReviewConfidence
    severity: ReviewSeverity = ReviewSeverity.warning
    source: ReviewFlagSource = ReviewFlagSource.ai_review
    context: str = ""


class FlagFeedbackRequest(BaseModel):
    flag_index: int = Field(ge=0)
    action: Literal["accepted", "dismissed", "edited"]


class FlagFeedbackResponse(BaseModel):
    id: uuid.UUID
    soap_note_id: uuid.UUID
    flag_index: int
    flag_issue_type: str
    flag_section: str
    action: str
    user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
