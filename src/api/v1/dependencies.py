from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from authx import TokenPayload
from src.config import security

from src.services.task_service import TaskService
from src.services.health_service import HealthService
from src.database.repositories.task import TaskRepository
from src.database import get_db
from src.database.repositories.health import HealthRepository
from src.database.models.users import UserDB
from src.storage.file_storage import FileStorage
from src.storage.dependencies import get_file_storage
from src.services.file_service import FileService
from src.services.exceptions import UserNotFound
from src.database.models.task import TaskDB
from src.database.repositories.user import UserRepository
from src.services.user_service import UserService
from src.services.exceptions import (
    UserInactive, UserNotFound, TaskNotFoundError, AccessDenied
)
from src.auth.permissions import get_scopes_for_role


SessionDep = Annotated[AsyncSession, Depends(get_db)]


def get_task_repository(db: SessionDep) -> TaskRepository:
    return TaskRepository(db)


TaskRepoDep = Annotated[TaskRepository, Depends(get_task_repository)]


def get_task_service(repo: TaskRepoDep,) -> TaskService:
    return TaskService(repo)

TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]



def get_user_repository(db: SessionDep):
    return UserRepository(db)

UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]

def get_user_service(repo: UserRepoDep) -> UserService:
    return UserService(repo)

UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def user_has_scopes(user: UserDB, *required: str, all_required: bool = True) -> bool:
    """Проверяет scopes по актуальной роли пользователя из БД."""
    actual_scopes = set(get_scopes_for_role(user.role.value))
    if all_required:
        return all(scope in actual_scopes for scope in required)
    return any(scope in actual_scopes for scope in required)





async def get_current_user(
    service: UserServiceDep,
    payload: TokenPayload = Depends(security.access_token_required),
) -> UserDB:
    """
    Проверяет JWT (подпись, срок действия) и возвращает активного пользователя из БД.
    """
    user_id = payload.sub
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Не удалось определить пользователя из токена'
        )

    return await service.get_active_user(int(user_id))
    


def require_scopes(*required_scopes: str, all_required: bool = True):
    """
    Фабрика зависимостей для проверки прав в токене.
    """
    async def scope_checker(
        current_user: UserDB = Depends(get_current_user),
        
    ) -> UserDB:
        if not user_has_scopes(current_user, *required_scopes, all_required=all_required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Недостаточно прав'
            )
        return current_user
    return scope_checker


def get_task_for_action(
    action_scope: str,
    own_scope: str,
    
):
    async def checker(
        task_id: int,
        service: TaskServiceDep,
        current_user: UserDB = Depends(get_current_user),
    )-> TaskDB:
        can_access_any = user_has_scopes(current_user, action_scope)
        if not can_access_any and not user_has_scopes(current_user, own_scope):
            raise AccessDenied()
        return await service.get_task_for_user(
            task_id,
            current_user.id,
            can_access_any=can_access_any,
        )
    return checker


def get_health_repository(db: SessionDep) -> HealthRepository:
    return HealthRepository(session=db)
HealthRepoDep = Annotated[HealthRepository, Depends(get_health_repository)]


def get_health_service(repo: HealthRepoDep) -> HealthService:
    return HealthService(repo=repo)


HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]

FileStorageDep = Annotated[FileStorage, Depends(get_file_storage)]

def get_file_service(
    repo: TaskRepoDep,
    storage: FileStorageDep,
) -> FileService:
    return FileService(repo, storage)


FileServiceDep = Annotated[FileService, Depends(get_file_service)]
# async def get_task_for_owner_or_admin(
#     task_id: int,
#     repo: TaskRepoDep,
#     current_user: UserDB = Depends(get_current_user),
# ) -> TaskDB:
#     """
#     Загружает задачу, если пользователь админ или если он владелец задачи, иначе пропускает.
#     """
#     task = repo.get(task_id)
#     if not task:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail='Задача не найдена'
#         )
#     if current_user.role == 'admin':
#         return task

#     if task.owner_id != current_user.id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail='Отсутсвуют права на эту задачу'
#         )
#     return task