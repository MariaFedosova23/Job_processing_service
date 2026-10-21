
from src.database.repositories.user import UserRepository
from src.auth.security import verify_password, get_password_hash
from src.database.models.users import UserDB
from src.services.exceptions import (
    InvalidCredentials, UserInactive, UserNotFound, UserAlreadyExists
)
from src.enums import Roles
import logging

logger = logging.getLogger('Job_processing_service')


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def get_active_user(self, user_id: int) -> UserDB:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise UserNotFound(user_id)
        if not user.is_active:
            raise UserInactive()
        return user

    async def authenticate(
        self,
        username: str,
        password: str,
    ) -> UserDB:
        user = await self.repo.get_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            raise InvalidCredentials()
        if not user.is_active:
            raise UserInactive()
        return user

    async def create_user(
        self, username: str, password: str, role: Roles
    ) -> UserDB:
        existing = await self.repo.get_by_username(username)
        if existing:
            raise UserAlreadyExists(username)
        user = await self.repo.create(
            username,
            password_hash=get_password_hash(password), 
            role=role,
            is_active=True

        )
        return user

    async def list_users(
        self,
        *,
        role: Roles | None,
        is_active: bool | None,
        limit,
        offset,
    ) -> list[UserDB]:
        return await self.repo.list_filtered(
            role=role, is_active=is_active, limit=limit, offset=offset,
        )


    async def get_or_raise(self, user_id: int) -> UserDB:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            logger.warning(
                'Пользователь не найден',
                extra={"event": "user_not_found", "user_id": user_id},
            )
            raise UserNotFound(user_id)
        return user


    async def patch_user(
        self,
        user_id: int,
        *,
        role: Roles | None = None,
        is_active: bool | None = None,
        
    ) -> UserDB:
        user = await self.get_or_raise(user_id)
        values: dict = {}
        if role is not None:
            values['role'] = role
        if is_active is not None:
            values['is_active'] = is_active
        if not values:
            return user
        
        user = await self.repo.update_user(
            user_id, values
        )
        logger.info(
            'Пользователь изменён: user_id=%s, fields=%s',
            user_id, list(values.keys()),
        )
        return user