"""add PCM audio checkpoint for resumable transcription

Stores the converted PCM in OSS so a run that fails mid-transcription can
re-transcribe only the failed chunks (identified via transcript
STATUS_FAILED_TRANSCRIPTION) without requiring a re-upload.

Revision ID: c3f8a71d5b42
Revises: eeb4a147c706
Create Date: 2026-04-13 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3f8a71d5b42'
down_revision: Union[str, Sequence[str], None] = 'eeb4a147c706'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'consultations',
        sa.Column('pcm_audio_oss_key', sa.String(length=500), nullable=True),
    )
    op.add_column(
        'consultations',
        sa.Column('pcm_audio_size_bytes', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('consultations', 'pcm_audio_size_bytes')
    op.drop_column('consultations', 'pcm_audio_oss_key')
