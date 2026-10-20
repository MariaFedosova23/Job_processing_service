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



SessionDep = Annotated[AsyncSession, Depends(get_db)]


def get_task_repository(db: SessionDep) -> TaskRepository:
    return TaskRepository(db)


TaskRepoDep = Annotated[TaskRepository, Depends(get_task_repository)]

FileStorageDep = Annotated[FileStorage, Depends(get_file_storage)]

def get_task_service(repo: TaskRepoDep,) -> TaskService:
    return TaskService(repo)

TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


def get_health_repository(db: SessionDep) -> HealthRepository:
    return HealthRepository(session=db)


HealthRepoDep = Annotated[HealthRepository, Depends(get_health_repository)]


def get_health_service(repo: HealthRepoDep) -> HealthService:
    return HealthService(repo=repo)


HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]

def get_file_service(
    repo: TaskRepoDep,
    storage: FileStorageDep,
) -> FileService:
    return FileService(repo, storage)


FileServiceDep = Annotated[FileService, Depends(get_file_service)]


async def get_current_user(
    db: SessionDep,
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
    user = db.get(UserDB, int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Пользователь не найден'
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Аккаунт деактивирован',
        )
    return user

