import logging
from typing import Callable
from datetime import datetime, timezone
from dataclasses import dataclass

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
EnqueueFn = Callable[[int], str]


@dataclass(frozen=True)
class StartProcessingResult:
    task: TaskDB
    celery_task_id: str


class TaskService:
    def __init__(self, repo: TaskRepository, enqueue: EnqueueFn | None = None):
        self.repo = repo
        self._enqueue = enqueue or (lambda _: None)

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
        task = await self.repo.get_with_result(task_id)
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

        task = await self.repo.update_status(task, Status.QUEUED)

        try:
            celery_task_id = self._enqueue(task_id)
            logger.info(
                "Запущена обработка задачи: task_id=%s", task_id,
                extra={"event": "task_processing_started", "task_id": task_id},
            )
        except Exception:
            logger.exception(
                "Не удалось поставить задачу в очередь: task_id=%s", task_id,
                extra={"event": "task_enqueue_failed", "task_id": task_id},
            )
            await self.repo.update_status(task, Status.NEW)
            raise
        return StartProcessingResult(task=task, celery_task_id=celery_task_id)
    
    async def begin_processing(
            self,
            task_id: int,
            *,
            allow_processing: bool = False,
        ) -> TaskDB | None:
        task = await self.repo.mark_processing(
            task_id,
            started_at=datetime.now(timezone.utc),
            allow_processing=allow_processing,
        )
        if task is None:
            logger.info(
                "Задача не в QUEUED (или PROCESSING при ретрае), пропускаем: task_id=%s",
                task_id,
                extra={"event": "task_skip_not_queued", "task_id": task_id},
            )
            return None
        logger.info(
            "Обработка начата: task_id=%s",
            task_id,
            extra={"event": "task_processing_begin", "task_id": task_id},
        )
        return task

    async def complete_processing(
        self,
        task_id: int,
        *,
        original_length: int,
        word_count: int,
    ) -> TaskDB | None:
        """
        Сохраняет результат и переводит PROCESSING → DONE.
        """
        now = datetime.now(timezone.utc)
        task = await self.repo.save_result_and_complete(
            task_id,
            original_length=original_length,
            word_count=word_count,
            processed_at=now,
            finished_at=now,
        )
        if task is None:
            return None
        logger.info(
            "Обработка завершена: task_id=%s", task_id,
            extra={"event": "task_processing_done", "task_id": task_id},
        )
        return task
    
    async def fail_processing(self, task_id: int, error: str) -> TaskDB | None:
        """
        PROCESSING → ERROR + текст ошибки.
        """
        task = await self.repo.mark_failed(
            task_id,
            error=error,
            finished_at=datetime.now(timezone.utc),
        )
        if task is None:
            logger.warning(
                "mark_failed: задача не найдена: task_id=%s", task_id,
                extra={"event": "task_fail_not_found", "task_id": task_id},
            )
            return None

        logger.error(
            "Обработка упала: task_id=%s, error=%s", task_id, error,
            extra={"event": "task_processing_failed", "task_id": task_id},
        )
        return task
