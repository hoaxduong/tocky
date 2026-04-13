"""add transcription checkpoint fields

Revision ID: c3f8a71d5b42
Revises: b4a2f1c9d3e7
Create Date: 2026-04-13 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3f8a71d5b42'
down_revision: Union[str, Sequence[str], None] = 'b4a2f1c9d3e7'
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
    op.add_column(
        'consultations',
        sa.Column(
            'chunks_total',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('0'),
        ),
    )
    op.add_column(
        'consultations',
        sa.Column(
            'chunks_completed',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('0'),
        ),
    )
    op.add_column(
        'consultations',
        sa.Column(
            'soap_generated',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )


def downgrade() -> None:
    op.drop_column('consultations', 'soap_generated')
    op.drop_column('consultations', 'chunks_completed')
    op.drop_column('consultations', 'chunks_total')
    op.drop_column('consultations', 'pcm_audio_size_bytes')
    op.drop_column('consultations', 'pcm_audio_oss_key')
