from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db_models.prompt_template import PromptTemplate

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


class PromptRegistry:
    """In-memory cache of active prompt templates, backed by PostgreSQL."""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def get(self, slug: str, **variables: str) -> str:
        """Return the active prompt for *slug*, with {variables} filled in."""
        template = self._cache[slug]
        if variables:
            template = template.format_map(variables)
        return template

    async def load(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Seed from files (if DB is empty) then load active prompts into cache."""
        async with session_factory() as db:
            await self._seed_if_empty(db)
            await self._load_active(db)

    async def refresh(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        slug: str | None = None,
    ) -> None:
        """Reload one or all active prompts from DB into cache."""
        async with session_factory() as db:
            await self._load_active(db, slug=slug)

    async def _seed_if_empty(self, db: AsyncSession) -> None:
        count = (
            await db.execute(select(func.count()).select_from(PromptTemplate))
        ).scalar_one()
        if count > 0:
            return

        logger.info("Seeding prompt templates from %s", PROMPTS_DIR)
        for path in sorted(PROMPTS_DIR.glob("*.md")):
            meta, content = _parse_prompt_file(path)
            db.add(
                PromptTemplate(
                    slug=meta["slug"],
                    version=1,
                    is_active=True,
                    title=meta.get("title", meta["slug"]),
                    description=meta.get("description", ""),
                    content=content,
                    variables=meta.get("variables", ""),
                )
            )
        await db.commit()
        logger.info("Seeded %d prompt templates", len(list(PROMPTS_DIR.glob("*.md"))))

    async def _load_active(self, db: AsyncSession, *, slug: str | None = None) -> None:
        query = select(PromptTemplate).where(
            PromptTemplate.is_active == True  # noqa: E712
        )
        if slug:
            query = query.where(PromptTemplate.slug == slug)
        result = await db.execute(query)
        for row in result.scalars():
            self._cache[row.slug] = row.content
        logger.info("Loaded %d active prompt(s) into cache", len(self._cache))


def _parse_prompt_file(path: Path) -> tuple[dict[str, str], str]:
    """Parse a .md file with YAML frontmatter. Returns (metadata_dict, content_str)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {"slug": path.stem}, text

    _, frontmatter, body = text.split("---", 2)
    meta: dict[str, str] = {}
    for line in frontmatter.strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    if "slug" not in meta:
        meta["slug"] = path.stem
    return meta, body.strip()
