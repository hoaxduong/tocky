"""Mock Elfie client that returns realistic hardcoded data for demo purposes.

All mock data is for patient "Mark" (Mark Thompson) — a newly diagnosed
Type 2 Diabetes patient, matching the sandbox consultation scenario.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from app.models.elfie import (
    ElfieBloodPressureReading,
    ElfieCarePlanRequest,
    ElfieLifestyleStats,
    ElfieMedication,
    ElfiePatientData,
    ElfiePushResult,
    ElfieVitalReading,
    ElfieVitals,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock data for Mark Thompson
# ---------------------------------------------------------------------------

_GLUCOSE_READINGS: list[ElfieVitalReading] = [
    ElfieVitalReading(date="2026-03-15", value=142, unit="mg/dL"),
    ElfieVitalReading(date="2026-03-17", value=148, unit="mg/dL"),
    ElfieVitalReading(date="2026-03-19", value=151, unit="mg/dL"),
    ElfieVitalReading(date="2026-03-21", value=145, unit="mg/dL"),
    ElfieVitalReading(date="2026-03-23", value=158, unit="mg/dL"),
    ElfieVitalReading(date="2026-03-25", value=162, unit="mg/dL"),
    ElfieVitalReading(date="2026-03-27", value=155, unit="mg/dL"),
    ElfieVitalReading(date="2026-03-29", value=149, unit="mg/dL"),
    ElfieVitalReading(date="2026-03-31", value=163, unit="mg/dL"),
    ElfieVitalReading(date="2026-04-02", value=157, unit="mg/dL"),
    ElfieVitalReading(date="2026-04-04", value=165, unit="mg/dL"),
    ElfieVitalReading(date="2026-04-07", value=160, unit="mg/dL"),
    ElfieVitalReading(date="2026-04-10", value=158, unit="mg/dL"),
    ElfieVitalReading(date="2026-04-13", value=155, unit="mg/dL"),
]

_BP_READINGS: list[ElfieBloodPressureReading] = [
    ElfieBloodPressureReading(date="2026-03-16", systolic=132, diastolic=85),
    ElfieBloodPressureReading(date="2026-03-19", systolic=138, diastolic=90),
    ElfieBloodPressureReading(date="2026-03-22", systolic=135, diastolic=87),
    ElfieBloodPressureReading(date="2026-03-25", systolic=140, diastolic=92),
    ElfieBloodPressureReading(date="2026-03-28", systolic=133, diastolic=86),
    ElfieBloodPressureReading(date="2026-03-31", systolic=137, diastolic=89),
    ElfieBloodPressureReading(date="2026-04-03", systolic=136, diastolic=88),
    ElfieBloodPressureReading(date="2026-04-06", systolic=134, diastolic=86),
    ElfieBloodPressureReading(date="2026-04-09", systolic=139, diastolic=91),
    ElfieBloodPressureReading(date="2026-04-12", systolic=135, diastolic=88),
]

_WEIGHT_READINGS: list[ElfieVitalReading] = [
    ElfieVitalReading(date="2026-03-23", value=93.2, unit="kg"),
    ElfieVitalReading(date="2026-03-30", value=93.0, unit="kg"),
    ElfieVitalReading(date="2026-04-06", value=93.4, unit="kg"),
    ElfieVitalReading(date="2026-04-13", value=93.1, unit="kg"),
]

_MARK_DATA = ElfiePatientData(
    patient_identifier="Mark",
    name="Mark Thompson",
    age=52,
    conditions=["Type 2 Diabetes Mellitus", "Hyperlipidemia"],
    member_since="2025-10-15",
    adherence_score=72,
    vitals=ElfieVitals(
        glucose=_GLUCOSE_READINGS,
        blood_pressure=_BP_READINGS,
        weight=_WEIGHT_READINGS,
    ),
    medications=[
        ElfieMedication(
            name="Atorvastatin",
            dose="20mg",
            frequency="Once daily",
            adherence_pct=65,
            missed_last_7d=3,
        ),
    ],
    lifestyle=ElfieLifestyleStats(
        avg_daily_steps=3200,
        avg_sleep_hours=5.8,
        avg_calories=2400,
    ),
    elfie_coins=1250,
    tier="Silver",
)

# Keyed by patient_identifier (case-insensitive)
_PATIENTS: dict[str, ElfiePatientData] = {
    "mark": _MARK_DATA,
}


class MockElfieClient:
    """Drop-in mock for the Elfie integration API."""

    def __init__(self, latency: float = 0.3) -> None:
        self.latency = latency

    async def get_patient_data(
        self, patient_identifier: str
    ) -> ElfiePatientData | None:
        await asyncio.sleep(self.latency)
        data = _PATIENTS.get(patient_identifier.strip().lower())
        if data:
            logger.debug("elfie mock: found patient %s", patient_identifier)
        else:
            logger.debug("elfie mock: no data for %s", patient_identifier)
        return data

    async def push_care_plan(
        self, request: ElfieCarePlanRequest
    ) -> ElfiePushResult:
        await asyncio.sleep(self.latency * 1.5)
        notification_id = str(uuid.uuid4())[:8]
        logger.info(
            "elfie mock: pushed %d care plan items for %s (notif=%s)",
            len(request.items),
            request.patient_identifier,
            notification_id,
        )
        return ElfiePushResult(
            success=True,
            notification_id=notification_id,
            message=f"Care plan sent to {request.patient_identifier}'s Elfie app",
        )
