"""add flag_feedback table

Revision ID: cc14b64f4796
Revises: 4e5c14c20541
Create Date: 2026-04-16 08:47:59.161399

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc14b64f4796'
down_revision: Union[str, Sequence[str], None] = '4e5c14c20541'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'flag_feedback',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('soap_note_id', sa.Uuid(), nullable=False),
        sa.Column('flag_index', sa.Integer(), nullable=False),
        sa.Column('flag_issue_type', sa.String(length=50), nullable=False),
        sa.Column('flag_section', sa.String(length=20), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_flag_feedback_soap_note_id'), 'flag_feedback', ['soap_note_id'])
    op.create_index(op.f('ix_flag_feedback_user_id'), 'flag_feedback', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_flag_feedback_user_id'), table_name='flag_feedback')
    op.drop_index(op.f('ix_flag_feedback_soap_note_id'), table_name='flag_feedback')
    op.drop_table('flag_feedback')
