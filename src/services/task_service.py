import os
import uuid
from pathlib import Path
import logging
from typing import Callable
from datetime import datetime, timezone
from dataclasses import dataclass

from fastapi import UploadFile

from src.enums import Caller, Status
from src.database.models.task import TaskDB
from src.database.models.file import FileDB
from src.schemas.tasks import TaskCreateSchema
from src.database.repositories.task import TaskRepository
from src.services.exceptions import (
    TaskNotFoundError,
    DuplicateExternalIdError,
    TaskCannotBeProcessedError,
    TaskCannotBeRetryError,
    TaskStateConflictError
)
from src.services.validator_task import (
    validate_task_can_be_cancelled,
    validate_transition_for_caller
)


from src.constants import ALLOWED_TYPES, MAX_FILE_SIZE

logger = logging.getLogger('job_processing_service')
EnqueueFn = Callable[[int, str], str]


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
        self,
        task_id: int,
        *,
        expected_status: Status,
        new_status: Status,
        caller: Caller
    ) -> TaskDB:
        task = await self.get_or_raise(task_id)
        validate_transition_for_caller(
            task_id, expected_status, new_status, caller
        )
        
        task = await self.repo.update_status(
            task_id,
            expected_status=expected_status,
            new_status=new_status,
        )
        if task is None:
            existing = await self.repo.get(task_id)
            if existing is None:
                raise TaskNotFoundError(task_id)
            raise TaskStateConflictError(task_id, expected_status)

        logger.info(
            "Статус задачи изменён: %s -> %s (caller=%s)",
            expected_status, new_status.value, caller.value,
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
        """NEW -> QUEUED -> PROCESSING -> DONE."""

        run_id = uuid.uuid4().hex
        task = await self.repo.mark_queued_new_task(task_id, run_id)

        if task is None:
            existing = await self.repo.get(task_id)
            if existing is None:
                logger.warning(
                    "Задача не найдена",
                    extra={"event": "task_not_found", "task_id": task_id},
                )
                raise TaskNotFoundError(task_id)
            logger.warning(
                "Задание нельзя обработать: status=%s",
                existing.status,
                extra={"event": "task_processing_failed", "task_id": task_id},
            )
            raise TaskCannotBeProcessedError(task_id, existing.status)
        
        try:
            celery_task_id = self._enqueue(task_id, run_id)
        
        except Exception:
            logger.exception(
                'Не удалось поставить задачу в очередь: task_id=%s, run_id=%s',
                task_id, run_id,
                extra={'event': 'task_enqueue_failed', 'task_id': task_id},
            )
            reverted = await self.repo.revert_to_new_status(
                task_id, run_id
            )
            if reverted is None:
                logger.info(
                    'Откат в NEW не выполнен: run_id устарел или статус изменился: task_id=%s, run_id=%s',
                    task_id, run_id,
                    extra={'event': 'task_revert_skipped', 'task_id': task_id},
                )
            raise

        logger.info(
            'Задача поставлена в очередь: task_id=%s, celery_task_id=%s, run_id=%s',
            task_id, celery_task_id, run_id,
            extra={'event': 'task_processing_started', 'task_id': task_id},
        )
        return StartProcessingResult(
            task=task,
            celery_task_id=celery_task_id
        )

    
    async def retry_task(self, task_id) -> TaskDB:
        """ERROR -> QUEUED-> PROCESSING -> DONE/ERROR."""
        run_id = uuid.uuid4().hex
        task = await self.repo.mark_queued_error_task(task_id, run_id)
        if task is None:
            existing = await self.repo.get(task_id)
            if existing is None:
                logger.warning(
                    "Задача не найдена",
                    extra={"event": "task_not_found", "task_id": task_id},
                )
                raise TaskNotFoundError(task_id)
            logger.warning(
                "Задание нельзя обработать: status=%s",
                existing.status,
                extra={"event": "task_processing_failed", "task_id": task_id},
            )
            raise TaskCannotBeRetryError(task_id, existing.status)

        try:
            celery_task_id = self._enqueue(task_id, run_id)
            
        except Exception as ex:
            logger.exception(
                "Не удалось поставить задачу в очередь: task_id=%s", task_id,
                extra={"event": "task_enqueue_failed", "task_id": task_id},
            )
            await self.repo.revert_to_error_status(
                task_id,
                run_id,
                error=str(ex)
            )
            raise
        logger.info(
            "Запущена обработка задачи: task_id=%s", task_id,
            extra={"event": "task_processing_retried", "task_id": task_id},
        )
        return StartProcessingResult(task=task, celery_task_id=celery_task_id)

    async def cancel_task(self, task_id) -> TaskDB:
        task = await self.get_or_raise(task_id)
        validate_task_can_be_cancelled(task_id, task.status)

        if task.status == Status.QUEUED:
            target_status = Status.CANCELLED
        else:
            target_status = Status.CANCELLING


        task_updated = await self.repo.update_status(
            task_id,
            expected_status=task.status,
            new_status = target_status
        )
        if task_updated is None:
            raise TaskStateConflictError(task_id, task.status)
        return task_updated
    
    async def begin_processing(
        self,
        task_id: int,
        run_id: str,
        *,
        allow_processing: bool = False,
        owner_token: str,
        lease_seconds: int,
    ) -> TaskDB | None:
        task = await self.repo.mark_processing(
            task_id,
            run_id,
            allow_processing=allow_processing,
            owner_token=owner_token,
            lease_seconds=lease_seconds,
        )
        if task is None:
            logger.info(
                "Задача не захвачена: task_id=%s, owner=%s",
                task_id, owner_token,
                extra={"event": "task_skip_not_queued", "task_id": task_id},
            )
            return None
        logger.info(
            "Обработка начата: task_id=%s, owner_token=%s, lease_until=%s",
            task_id, owner_token, task.lease_until,
            extra={"event": "task_processing_begin", "task_id": task_id},
        )
        return task


    async def complete_processing(
        self,
        task_id: int,
        *,
        owner_token: str,
        original_length: int,
        word_count: int,
        run_id: str,
    ) -> TaskDB | None:
        """
        Сохраняет результат и переводит PROCESSING → DONE.
        """

        task = await self.repo.save_result_and_complete(
            task_id,
            original_length=original_length,
            word_count=word_count,
            owner_token=owner_token,
            run_id=run_id,
        )
        if task is None:
            logger.info(
                'Статус задачи изменился во время обработки. Проверяем на отмену...'
            )
            cancelled = await self.repo.confirm_cancellation(
                task_id, owner_token=owner_token
            )
            if cancelled:
                logger.info('Задача успешно переведена в CANCELLED из-за внешней отмены.')
                
            else: 
                logger.warning('Не удалось сохранить результат и подтвердить отмену. task_id=%s', task_id)
            return
        logger.info(
            "Обработка завершена: task_id=%s", task_id,
            extra={"event": "task_processing_done", "task_id": task_id},
        )
        return task
    
    async def fail_processing(
            self, task_id: int, error: str, owner_token: str
    ) -> TaskDB | None:
        """
        PROCESSING → ERROR
        """
        task = await self.repo.mark_failed(
            task_id,
            error=error,
            owner_token=owner_token,
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

    async def release_for_retry(
        self,
        task_id: int,
        *,
        owner_token: str,
    ) -> TaskDB | None:
        task = await self.repo.release_to_queued(
            task_id, owner_token=owner_token,
        )
        if task is None:
            logger.warning(
                "release_for_retry: нет владелец или статус не PROCESSING: "
                "task_id=%s, owner_token=%s",
                task_id, owner_token,
                extra={"event": "task_release_failed", "task_id": task_id},
            )
        else:
            logger.info(
                "Задача возвращена в QUEUED для ретрая: task_id=%s",
                task_id,
                extra={"event": "task_released_for_retry", "task_id": task_id},
            )
        return task




    async def upload_file(
        self,
        task_id: int,
        file: UploadFile,
    ) -> FileDB:

        task = await self.repo.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        # Проверка MIME
        if file.content_type not in ALLOWED_TYPES:
            raise ValueError(
                f'Неподдерживаемый тип файла: {file.content_type}'
            )

        contents = await file.read()
        size = len(contents)
        if size > MAX_FILE_SIZE:
            raise ValueError('Файл превышает лимит 10 МБ')
        
        upload_dir = os.getenv("UPLOAD_DIR", "/app/files")
        Path(upload_dir).mkdir(parents=True, exist_ok=True)

        suffix = Path(file.filename).suffix or ".bin"
        internal_name = f"{uuid.uuid4().hex}{suffix}"
       
        final_path = Path(upload_dir) / internal_name
        final_path.write_bytes(contents)
   
        # Создаём запись в БД
        file_db = await self.repo.create_file(
            task_id=task_id,
            original_name=file.filename,
            internal_name=internal_name,
            mime_type=file.content_type,
            size_bytes=size,
        )

        logger.info(
            "Файл загружен: task_id=%s, file_id=%s, internal_name=%s",
            task_id, file_db.id, internal_name,
            extra={"event": "file_uploaded", "task_id": task_id, "file_id": file_db.id},
        )
        from src.worker.tasks.tasks import get_file
        get_file.delay(task_id, internal_name)
        
        return file_db