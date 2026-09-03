"""
Auth & Identity Domain Repository.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User


class UserRepository:
    async def get(self, session: AsyncSession, user_id: UUID) -> User | None:
        return await session.get(User, user_id)

    async def get_by_google_sub(self, session: AsyncSession, google_sub: str) -> User | None:
        return await session.scalar(select(User).where(User.google_sub == google_sub))

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        return await session.scalar(select(User).where(User.email == email))

    async def create(self, session: AsyncSession, user: User) -> User:
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    async def update(self, session: AsyncSession, user: User) -> User:
        await session.commit()
        await session.refresh(user)
        return user
