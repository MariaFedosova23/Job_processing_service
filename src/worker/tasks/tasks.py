import logging
import asyncio
from datetime import datetime, timezone


from sqlalchemy.exc import OperationalError
from src.worker.app import celery
from src.database.database import get_session
from src.database.models.task import TaskDB, TaskResultDB
from src.database.repositories.task import TaskRepository
from src.enums import Status
from src.constants import (
    MAX_TRIES,
    RETRY_BACKOFF_MAX,
    TIME_CELERY_TASK,
    FORBIDDEN_WORD_IN_TEXT
)
from src.services.task_service import TaskService
from src.services.exceptions import ForbiddenWordsError, TaskProcessingError

logger = logging.getLogger('job_processing_service')


@celery.task(
    bind=True,
    name='worker.process_task',
    acks_late=True,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_backoff_max=RETRY_BACKOFF_MAX,
    max_retries=MAX_TRIES
)
def process_task(self, task_id: int) -> None:
    asyncio.run(process_task_async(task_id))


async def process_task_async(task_id: int) -> None:
    async with get_session() as session:
        service = TaskService(
            TaskRepository(session)
        )
        task = await service.begin_processing(task_id)
        if task is None:
            return
        
        text = task.text
    try:
        found = [word for word in FORBIDDEN_WORD_IN_TEXT if word in text.lower()]
        if found:
            raise ForbiddenWordsError(found)

        original_length = len(text)
        word_count = len(text.split())
        
        await asyncio.sleep(TIME_CELERY_TASK)

        async with get_session() as session:
            service = TaskService(
                TaskRepository(session)
            )
            await service.complete_processing(
                task_id,
                original_length=original_length,
                word_count=word_count,
            )
    except OperationalError:
        raise
    except TaskProcessingError as exc:
        logger.warning(
            "Бизнес-ошибка обработки: task_id=%s, error=%s",
            task_id, exc,
            extra={"event": "task_processing_business_error", "task_id": task_id},
        )
        async with get_session() as session:
            service = TaskService(
                TaskRepository(session)
            )
            await service.fail_processing(task_id, error=str(exc))

    except Exception as exc:
        logger.exception(
            "Непредвиденная ошибка обработки: task_id=%s",
            task_id,
            extra={"event": "task_processing_unexpected_error", "task_id": task_id},
        )
        async with get_session() as session:
            service = TaskService(
                TaskRepository(session)
            )
            await service.fail_processing(
                task_id,
                error=f'Внутренняя ошибка: {type(exc).__name__}',
            )
        



    




