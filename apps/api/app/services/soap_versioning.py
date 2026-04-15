"""SOAP note version archiving service.

Archives snapshots of SOAP notes before mutations so that the full edit
history (AI draft → doctor corrections → finalized) is preserved.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.db_models.soap_note_version import SOAPNoteVersion

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db_models.soap_note import SOAPNote

logger = logging.getLogger(__name__)


async def archive_soap_snapshot(
    db: AsyncSession,
    soap: SOAPNote,
    source: str,
    edited_by: str | None = None,
) -> SOAPNoteVersion | None:
    """Snapshot the current state of *soap* before the caller mutates it.

    The ``version`` on the snapshot matches ``soap.version`` at call time
    (i.e. before the caller increments it).

    Returns ``None`` if a snapshot for this (soap_note_id, version) pair
    already exists (idempotent — safe to call multiple times).
    """
    # Check if this version is already archived
    existing = await db.execute(
        select(SOAPNoteVersion.id).where(
            SOAPNoteVersion.soap_note_id == soap.id,
            SOAPNoteVersion.version == soap.version,
        )
    )
    if existing.scalar_one_or_none() is not None:
        logger.debug(
            "Version %d for SOAP %s already archived, skipping",
            soap.version,
            soap.id,
        )
        return None

    version = SOAPNoteVersion(
        soap_note_id=soap.id,
        version=soap.version,
        subjective=soap.subjective,
        objective=soap.objective,
        assessment=soap.assessment,
        plan=soap.plan,
        medical_entities=soap.medical_entities or {},
        icd10_codes=soap.icd10_codes or [],
        review_flags=soap.review_flags or [],
        is_draft=soap.is_draft,
        source=source,
        edited_by=edited_by,
    )
    db.add(version)
    return version


async def archive_initial_version(
    db: AsyncSession,
    soap: SOAPNote,
) -> SOAPNoteVersion | None:
    """Archive the AI-generated v1 right after a new SOAPNote is created.

    The caller must ``await db.flush()`` before calling this so that
    ``soap.id`` is populated.
    """
    return await archive_soap_snapshot(db, soap, source="ai_generated")
