import logging
from fastapi import (
    APIRouter, Query
)

from src.schemas.users import (
    PatchUserSchema
)
from src.schemas.users import UserResponseSchema, CreateUserSchema
from src.api.v1.dependencies import UserServiceDep
from src.enums import Roles
from src.constants import (
    DEFAULT_LIMIT_USERS,
    MAX_LIMIT_USERS,
    MIN_LIMIT_USERS,
    MIN_OFFSET,
    DEFAULT_OFFSET
)


logger = logging.getLogger('job_processing_service')

router = APIRouter(prefix='/api/v1/users', tags=['users'])


@router.post(
    '/',
    summary='Создание пользователя',
    response_model=UserResponseSchema
)
async def create_user(
    service: UserServiceDep,
    creds: CreateUserSchema
):
    return await service.create_user(
        creds.username,
        creds.password,
        creds.role
    )

@router.get(
    '/',
    response_model=list[UserResponseSchema],
    summary='Получить список пользователей',
)
async def get_users(
    service: UserServiceDep,
    role: Roles | None = Query(
        None, description='Фильтр по роле пользователя'
    ),
    is_active: bool | None = Query(
        None, description='Фильтр по активности пользователя'
    ),
    limit: int = Query(
        default=DEFAULT_LIMIT_USERS,
        ge=MIN_LIMIT_USERS,
        le=MAX_LIMIT_USERS,
    ),
    offset: int = Query(
        default=DEFAULT_OFFSET,
        ge=MIN_OFFSET,
    )
) -> list[UserResponseSchema]:
    return await service.list_users(
        role=role, is_active=is_active, limit=limit, offset=offset
    )

@router.get(
    '/{user_id}',
    response_model=UserResponseSchema,
    summary='Получить пользователя',
)
async def get_user(
    service: UserServiceDep,
    user_id: int

) -> UserResponseSchema:
    return await service.get_or_raise(user_id)

@router.patch(
        path='/{user_id}/',
        response_model=UserResponseSchema,
        summary='Изменение пользователя',
)
async def patch_user(
    payload: PatchUserSchema,
    user_id: int,
    service: UserServiceDep
) -> UserResponseSchema:
    return await service.patch_user(
        user_id,
        role=payload.role,
        is_active=payload.is_active,
    )