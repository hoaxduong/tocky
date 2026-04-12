"""Create the initial admin user.

Usage:
    cd apps/api
    uv run python -m app.scripts.create_admin
    uv run python -m app.scripts.create_admin \
        --email admin@tocky.local --password secret123
"""

import argparse
import asyncio
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db_models.user import User
from app.services.auth import hash_password


async def create_admin(email: str, password: str, name: str) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        db: AsyncSession
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            if existing.role == "admin":
                print(f"Admin user already exists: {email}")
            else:
                existing.role = "admin"
                await db.commit()
                print(f"Updated existing user to admin: {email}")
            await engine.dispose()
            return

        user = User(
            id=str(uuid4()),
            name=name,
            email=email,
            password_hash=hash_password(password),
            role="admin",
        )
        db.add(user)
        await db.commit()
        print(f"Admin user created: {email} (ID: {user.id})")

    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Create initial admin user")
    parser.add_argument("--email", default="admin@tocky.dev")
    parser.add_argument("--password", default="admin123456")
    parser.add_argument("--name", default="Admin")
    args = parser.parse_args()

    asyncio.run(create_admin(args.email, args.password, args.name))


if __name__ == "__main__":
    main()
