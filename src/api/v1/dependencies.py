from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.task_service import TaskService
from src.services.health_service import HealthService
from src.database.repositories.task import TaskRepository
from src.database import get_db
from src.worker.dispatcher import enqueue_process_task, enequeu_get_file
from src.database.repositories.health import HealthRepository



SessionDep = Annotated[AsyncSession, Depends(get_db)]


def get_task_repository(db: SessionDep) -> TaskRepository:
    return TaskRepository(db)


TaskRepoDep = Annotated[TaskRepository, Depends(get_task_repository)]


def get_task_service(repo: TaskRepoDep) -> TaskService:
    return TaskService(repo, enqueue=enqueue_process_task)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


def get_health_repository(db: SessionDep) -> HealthRepository:
    return HealthRepository(session=db)


HealthRepoDep = Annotated[HealthRepository, Depends(get_health_repository)]


def get_health_service(repo: HealthRepoDep) -> HealthService:
    return HealthService(repo=repo)


HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]