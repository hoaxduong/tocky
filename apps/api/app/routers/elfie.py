"""Elfie integration endpoints — patient data pull & care plan push."""

import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.dependencies import CurrentUserDep
from app.models.elfie import ElfieCarePlanRequest, ElfiePatientData, ElfiePushResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/elfie", tags=["elfie"])


@router.get("/patient/{patient_identifier}", response_model=ElfiePatientData)
async def get_elfie_patient(
    patient_identifier: str,
    request: Request,
    user: CurrentUserDep,
):
    """Fetch Elfie patient data by identifier."""
    client = request.app.state.elfie_client
    data = await client.get_patient_data(patient_identifier)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Elfie data found for patient '{patient_identifier}'",
        )
    return data


@router.post("/push-care-plan", response_model=ElfiePushResult)
async def push_care_plan(
    body: ElfieCarePlanRequest,
    request: Request,
    user: CurrentUserDep,
):
    """Push a care plan to a patient's Elfie app."""
    client = request.app.state.elfie_client
    result = await client.push_care_plan(body)
    return result
