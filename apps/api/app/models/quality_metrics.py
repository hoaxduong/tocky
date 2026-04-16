from datetime import datetime

from pydantic import BaseModel


class SectionEditMetrics(BaseModel):
    section: str
    avg_edit_distance: float  # normalized 0-1 (0 = identical, 1 = completely different)
    pct_edited: float  # percentage of consultations where this section was changed
    total_compared: int


class QualityMetricsResponse(BaseModel):
    overall_edit_rate: float  # % of consultations with any doctor edits
    total_finalized: int
    total_with_history: int  # finalized consultations that have version history
    by_section: list[SectionEditMetrics]
    by_language: dict[str, list[SectionEditMetrics]]
    period_start: datetime | None = None
    period_end: datetime | None = None


class FlagTypeStats(BaseModel):
    issue_type: str
    total: int
    accepted: int
    dismissed: int
    acceptance_rate: float


class FlagStatsResponse(BaseModel):
    total_flags: int
    total_feedback: int
    by_issue_type: list[FlagTypeStats]
    by_section: list[FlagTypeStats]
