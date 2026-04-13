"""add icd10 codes table and soap_notes icd10_codes column

Revision ID: f7d9e2a1b3c5
Revises: a1b2c3d4e5f6
Create Date: 2026-04-13 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f7d9e2a1b3c5"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable pg_trgm extension for fuzzy text search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "icd10_codes",
        sa.Column("code", sa.String(10), primary_key=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "descriptions",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("category", sa.String(5), nullable=False, index=True),
    )

    # GIN trigram index on description for fuzzy search
    op.execute(
        "CREATE INDEX ix_icd10_codes_description_trgm "
        "ON icd10_codes USING gin (description gin_trgm_ops)"
    )

    # Add icd10_codes JSON column to soap_notes
    op.add_column(
        "soap_notes",
        sa.Column(
            "icd10_codes",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )


def downgrade() -> None:
    op.drop_column("soap_notes", "icd10_codes")
    op.drop_index("ix_icd10_codes_description_trgm", table_name="icd10_codes")
    op.drop_table("icd10_codes")
