from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.task_service import TaskService
from src.database.repositories.task import TaskRepository
from src.database import get_db
from src.worker.dispatcher import enqueue_process_task


SessionDep = Annotated[AsyncSession, Depends(get_db)]


def get_task_repository(db: SessionDep) -> TaskRepository:
    return TaskRepository(db)


TaskRepoDep = Annotated[TaskRepository, Depends(get_task_repository)]


def get_task_service(repo: TaskRepoDep) -> TaskService:
    return TaskService(repo, enqueue=enqueue_process_task)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


# async def get_task_process_service(
#     session: AsyncSession = Depends(get_db),
# ) -> TaskService:
#     repo = TaskRepository(session)
#     return TaskService(repo, enqueue=enqueue_process_task)


# TaskServiceProcessDep = Annotated[
#     TaskService, Depends(get_task_process_service)
# ]