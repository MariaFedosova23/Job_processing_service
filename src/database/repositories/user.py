
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.users import UserDB
from src.enums import Roles


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> UserDB | None:
        return await self.session.get(UserDB, user_id)

    async def get_by_username(self, username: str) -> UserDB | None:
        result = await self.session.execute(
            select(UserDB).where(UserDB.username == username)
        )
        return result.scalar_one_or_none()

    async def create(
            self,
            username: str,
            password_hash: str,
            role: Roles,
            is_active: bool
        ) -> UserDB:
        user = UserDB(
            username=username,
            password_hash=password_hash,
            role=role,
            is_active=is_active
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user


    async def list_filtered(
        self,
        *,
        role: Roles | None = None,
        is_active: bool | None = None,
        limit: int,
        offset: int,
    ) -> list[UserDB]:
        stmt = select(UserDB)
        if role is not None:
            stmt = stmt.where(UserDB.role == role)
        if is_active is not None:
            stmt = stmt.where(UserDB.is_active == is_active)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())



    async def update_status(
        self,
        user_id: int,
    ) -> UserDB | None:
        """Обновление пользователя."""

        stmt = (
            update(UserDB)
            .where(UserDB.id == user_id)
            .where(TaskDB.status == expected_status) 
            .values(**values)
            .returning(TaskDB)
        )
        result = await self.session.execute(stmt)
        task = result.scalar_one_or_none()
        await self.session.commit()
        return task
