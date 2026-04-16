"""Seed demo users (admin + doctor). Idempotent — skips if email exists."""

import asyncio
import logging

from sqlalchemy import select

from app.config import get_settings
from app import database as _db
from app.database import init_db, close_db
from app.db_models.user import User
from app.services.auth import hash_password

logger = logging.getLogger(__name__)

DEMO_USERS = [
    {
        "name": "Admin",
        "email": "admin@tocky.dev",
        "password": "admin123",
        "role": "admin",
    },
    {
        "name": "Dr. Demo",
        "email": "doctor@tocky.dev",
        "password": "doctor123",
        "role": "doctor",
    },
]


async def seed() -> None:
    settings = get_settings()
    await init_db(settings.database_url)
    assert _db.async_session_factory is not None

    async with _db.async_session_factory() as session:
        for user_data in DEMO_USERS:
            exists = await session.scalar(
                select(User.id).where(User.email == user_data["email"])
            )
            if exists:
                logger.info("User %s already exists, skipping", user_data["email"])
                continue

            user = User(
                name=user_data["name"],
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                role=user_data["role"],
            )
            session.add(user)
            logger.info("Created %s user: %s", user_data["role"], user_data["email"])

        await session.commit()

    await close_db()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed())
