"""add french language support

Revision ID: a1b2c3d4e5f6
Revises: eff2ea357dce
Create Date: 2026-04-13 20:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "eff2ea357dce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SOAP_FR_CONTENT = (
    "Vous êtes un assistant clinique professionnel. "
    "À partir de la transcription de la consultation médicale, "
    "générez une note SOAP en français en utilisant la "
    "terminologie médicale standard."
    "\n\n"
    "Format :\n"
    "## Subjective\n<contenu>\n\n"
    "## Objective\n<contenu>\n\n"
    "## Assessment\n<contenu>\n\n"
    "## Plan\n<contenu>"
)

_LANGUAGE_DETECTION_CONTENT = (
    "Detect the language of the given text. "
    "Reply with exactly one of these codes: "
    "vi, ar-eg, ar-gulf, en, fr. "
    "If unsure, reply en. Output only the code, nothing else."
)

_SOAP_FR_DESCRIPTION = (
    "Generates SOAP notes in French "
    "with standard medical terminology."
)


def upgrade() -> None:
    """Insert soap_fr prompt and update language_detection."""
    prompt_templates = sa.table(
        "prompt_templates",
        sa.column("id", sa.String),
        sa.column("slug", sa.String),
        sa.column("version", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("title", sa.String),
        sa.column("description", sa.Text),
        sa.column("content", sa.Text),
        sa.column("variables", sa.Text),
    )

    # Insert soap_fr prompt (only if it doesn't already exist)
    conn = op.get_bind()
    existing = conn.execute(
        sa.select(prompt_templates.c.id).where(
            prompt_templates.c.slug == "soap_fr"
        )
    ).first()

    if not existing:
        op.execute(
            prompt_templates.insert().values(
                id=sa.text("gen_random_uuid()"),
                slug="soap_fr",
                version=1,
                is_active=True,
                title="SOAP Generation - French",
                description=_SOAP_FR_DESCRIPTION,
                content=_SOAP_FR_CONTENT,
                variables="",
            )
        )

    # Update language_detection prompt to include fr
    op.execute(
        prompt_templates.update()
        .where(prompt_templates.c.slug == "language_detection")
        .where(prompt_templates.c.is_active == True)  # noqa: E712
        .values(content=_LANGUAGE_DETECTION_CONTENT)
    )


def downgrade() -> None:
    """Remove soap_fr prompt and revert language_detection."""
    prompt_templates = sa.table(
        "prompt_templates",
        sa.column("slug", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("content", sa.Text),
    )

    op.execute(
        prompt_templates.delete().where(
            prompt_templates.c.slug == "soap_fr"
        )
    )

    op.execute(
        prompt_templates.update()
        .where(prompt_templates.c.slug == "language_detection")
        .where(prompt_templates.c.is_active == True)  # noqa: E712
        .values(
            content=(
                "Detect the language of the given text. "
                "Reply with exactly one of these codes: "
                "vi, ar-eg, ar-gulf, en. "
                "If unsure, reply en. "
                "Output only the code, nothing else."
            )
        )
    )
