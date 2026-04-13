"""add full audio columns and review flags

Revision ID: b4a2f1c9d3e7
Revises: 2e1ad0cc1690
Create Date: 2026-04-12 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b4a2f1c9d3e7'
down_revision: Union[str, Sequence[str], None] = '2e1ad0cc1690'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'consultations',
        sa.Column('full_audio_oss_key', sa.String(length=500), nullable=True),
    )
    op.add_column(
        'consultations',
        sa.Column('full_audio_duration_ms', sa.Integer(), nullable=True),
    )
    op.add_column(
        'soap_notes',
        sa.Column(
            'review_flags',
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )


def downgrade() -> None:
    op.drop_column('soap_notes', 'review_flags')
    op.drop_column('consultations', 'full_audio_duration_ms')
    op.drop_column('consultations', 'full_audio_oss_key')
