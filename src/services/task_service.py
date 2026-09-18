import logging


from asyncio import sleep

from src.database import AsyncSessionLocal
from src.database.models.task import TaskDB
from src.schemas.tasks import Status, TaskCreateSchema
from src.database.repositories.task import TaskRepository
from src.services.exceptions import (
    TaskNotFoundError,
    DuplicateExternalIdError,
)
from src.services.validator_task import (
    validate_status_transition,
    validate_task_can_be_processed
)

logger = logging.getLogger('job_processing_service')


class TaskService:
    def __init__(self, repo: TaskRepository):
        self.repo = repo

    async def list_tasks(
            self,
            *,
            status: Status | None,
            priority: int | None,
            limit,
            offset,
    ) -> list[TaskDB]:
        return await self.repo.list_filtered(
            status=status, priority=priority, limit=limit, offset=offset,
        )

    async def get_or_raise(self, task_id: int) -> TaskDB:
        task = await self.repo.get(task_id)
        if task is None:
            logger.warning(
                "Задача не найдена",
                extra={"event": "task_not_found", "task_id": task_id},
            )
            raise TaskNotFoundError(task_id)
        return task

    async def create(self, data: TaskCreateSchema) -> TaskDB:
        existing = await self.repo.get_by_external_id(data.external_id)
        if existing is not None:
            raise DuplicateExternalIdError(data.external_id)
        task = TaskDB(
            title=data.title,
            text=data.text,
            priority=data.priority,
            external_id=data.external_id,
        )
        task = await self.repo.add(task)
    
        logger.info(
            "Задача создана: external_id=%s",
            data.external_id,
            extra={"event": "task_created", "task_id": task.id},
        )
        return task

    async def change_status(
        self, task_id: int, new_status: Status
    ) -> TaskDB:
        task = await self.get_or_raise(task_id)
        old_status = task.status
        validate_status_transition(task_id, old_status, new_status.value)
        task = await self.repo.update_status(task, new_status)

        logger.info(
            "Статус задачи изменён: %s -> %s",
            old_status, new_status.value,
            extra={"event": "task_status_changed", "task_id": task.id},
        )
        return task

    async def delete(self, task_id: int) -> None:
        task = await self.get_or_raise(task_id)
        try:
            await self.repo.delete(task)
        except Exception:
            logger.exception(
                "Ошибка БД при удалении задачи: task_id=%s",
                task_id,
                extra={"event": "task_delete_failed", "task_id": task_id},
            )
            raise

        logger.info(
            "Задача удалена: task_id=%s",
            task_id,
            extra={"event": "task_deleted", "task_id": task_id},
        )

    async def start_processing(self, task_id: int) -> TaskDB:
        task = await self.get_or_raise(task_id)
        validate_task_can_be_processed(task_id, task.status)

        task = await self.repo.update_status(task, Status.PROCESSING)

        logger.info(
            "Запущена обработка задачи: task_id=%s",
            task_id,
            extra={"event": "task_processing_started", "task_id": task_id},
        )
        return task

    @staticmethod
    async def process(task_id: int, delay: int) -> None:
        await sleep(delay)
        async with AsyncSessionLocal() as session:
            repo = TaskRepository(session)
            task = await repo.get(task_id)
            if task is None:
                logger.warning(
                    "Задача не найдена во время обработки: task_id=%s",
                    task_id,
                    extra={"event": "task_not_found", "task_id": task_id},
                )
                return
            try:
                await repo.update_status(task, Status.DONE)
                logger.info(
                    "Задача обработана: task_id=%s",
                    task_id,
                    extra={
                        "event": "task_processing_done",
                        "task_id": task_id,
                    },
                )
            except Exception:
                logger.exception(
                    "Ошибка при фоновой обработке: task_id=%s",
                    task_id,
                    extra={
                        "event": "task_processing_failed",
                        "task_id": task_id,
                    },
                )
               
