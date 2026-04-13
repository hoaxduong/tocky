"""Pydantic schemas for the Elfie chronic disease management integration."""

from __future__ import annotations

from pydantic import BaseModel


class ElfieVitalReading(BaseModel):
    date: str
    value: float
    unit: str


class ElfieBloodPressureReading(BaseModel):
    date: str
    systolic: int
    diastolic: int


class ElfieVitals(BaseModel):
    glucose: list[ElfieVitalReading]
    blood_pressure: list[ElfieBloodPressureReading]
    weight: list[ElfieVitalReading]


class ElfieMedication(BaseModel):
    name: str
    dose: str
    frequency: str
    adherence_pct: int
    missed_last_7d: int


class ElfieLifestyleStats(BaseModel):
    avg_daily_steps: int
    avg_sleep_hours: float
    avg_calories: int


class ElfiePatientData(BaseModel):
    patient_identifier: str
    name: str
    age: int
    conditions: list[str]
    member_since: str
    adherence_score: int
    vitals: ElfieVitals
    medications: list[ElfieMedication]
    lifestyle: ElfieLifestyleStats
    elfie_coins: int
    tier: str


class ElfieCarePlanItem(BaseModel):
    category: str
    action: str
    details: str


class ElfieCarePlanRequest(BaseModel):
    consultation_id: str
    patient_identifier: str
    items: list[ElfieCarePlanItem]


class ElfiePushResult(BaseModel):
    success: bool
    notification_id: str
    message: str
