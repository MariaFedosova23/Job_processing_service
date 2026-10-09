import logging
import asyncio
import os
from pathlib import Path
from sqlalchemy.exc import OperationalError
import uuid
from src.worker.lease import watch_lease, LeaseLostError, run_with_lease

from src.worker.app import celery
from src.database.database import get_session
from src.database.repositories.task import TaskRepository
from src.constants import (
    MAX_TRIES,
    RETRY_BACKOFF_MAX,
    TIME_CELERY_TASK,
    FORBIDDEN_WORD_IN_TEXT,
    LEASE_SECONDS,
    SOFT_TIME,
    TIME_LIMIT,
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
    max_retries=MAX_TRIES,
    retry_jitter=True,
    soft_time_limit=SOFT_TIME,
    time_limit=TIME_LIMIT,
)
def process_task(self, task_id: int, run_id: str) -> None:
    is_final_attempt = self.request.retries >= self.max_retries
    celery_task_id = self.request.id

    asyncio.run(
        process_task_async(
            task_id,
            run_id=run_id,
            celery_task_id=celery_task_id,
            attempt=self.request.retries,
            is_final_attempt=is_final_attempt,
        )
    )


async def process_task_async(
        task_id: int,
        run_id: str,
        celery_task_id: str,
        attempt: int = 0,
        is_final_attempt: bool = False,
        
) -> None:
    logger.info(
        "Начало обработки задачи: task_id=%s, celery_task_id=%s",
        task_id, celery_task_id,
        extra={'event': 'task_processing_started', 'task_id': task_id},
    )
    owner_token = str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    claim_started = loop.time()

    async with get_session() as session:
        service = TaskService(
            TaskRepository(session)
        )
        task = await service.begin_processing(
            task_id,
            run_id,
            allow_processing=attempt > 0,
            owner_token=owner_token,
            lease_seconds = LEASE_SECONDS
        )
        if task is None:
            return None

        
        text = task.text
    

    try:
        logger.info('Запускаем задачи')
        original_length, word_count = await run_with_lease(
            work=calculate_result(text),
            guard=watch_lease(
                task_id,
                owner_token,
                initial_deadline=claim_started + LEASE_SECONDS,
                lease_seconds=LEASE_SECONDS,
            ),
        )
    except LeaseLostError:

        async with get_session() as session:
            repo = TaskRepository(session)
            cancelled = await repo.confirm_cancellation(
                task_id,
                owner_token=owner_token,
            )
    
        if cancelled:
            logger.info(
                "Задача отменена и подтверждена: task_id=%s",
                task_id,
                extra={'event': 'task_cancelled', 'task_id': task_id},
            )
        else:
            logger.warning(
                "Обработка прекращена: владение потеряно: task_id=%s",
                task_id,
                extra={'event': 'task_result_dropped', 'task_id': task_id},
            )
        return
    
    except ForbiddenWordsError as exc:
        logger.warning(
            "Бизнес-ошибка обработки: task_id=%s, error=%s",
            task_id, exc,
            extra={
                "event": "task_processing_business_error",
                "task_id": task_id
            },
        )
        async with get_session() as session:
            service = TaskService(
                TaskRepository(session)
            )
            await service.fail_processing(
                task_id,
                owner_token=owner_token,
                error=str(exc))
        return

    try:
        async with get_session() as session:
            service = TaskService(
                TaskRepository(session)
            )
            saved = await service.complete_processing(
                task_id,
                owner_token=owner_token,
                original_length=original_length,
                word_count=word_count,
                run_id=run_id,
            )
    except OperationalError:
        if is_final_attempt:
            logger.exception(
                'Исчерпаны попытки обработки: task_id=%s', task_id,
                extra={
                    'event': 'task_retries_retries_exhausted',
                    'task_id': task_id
                },
            )
            return
        try:
            async with get_session() as session:
                service = TaskService(TaskRepository(session))
                await service.release_for_retry(
                    task_id, owner_token=owner_token,
                )
        except Exception:
            logger.exception(
                'Не удалось освободить задачу перед ретраем: task_id=%s',
                task_id,
                extra={"event": "task_release_error", "task_id": task_id},
            )
        raise

    except TaskProcessingError as exc:
        logger.warning(
            "Бизнес-ошибка обработки: task_id=%s, error=%s",
            task_id, exc,
            extra={
                "event": "task_processing_business_error",
                "task_id": task_id
            },
        )
        async with get_session() as session:
            service = TaskService(
                TaskRepository(session)
            )
            await service.fail_processing(
                task_id,
                owner_token=owner_token,
                error=str(exc))
        return


    except Exception as exc:
        logger.exception(
            'Непредвиденная ошибка обработки: task_id=%s, celery_task_id=%s',
            task_id, celery_task_id,
            extra={
                'event': 'task_processing_unexpected_error', 'task_id': task_id
            },
        )
        async with get_session() as session:
            service = TaskService(
                TaskRepository(session)
            )
            await service.fail_processing(
                task_id,
                owner_token=owner_token,
                error=f'Внутренняя ошибка: {type(exc).__name__}',
            )
        return
    
    if saved is None:
        logger.warning(
            "Не удалось сохранить результат — lease истёк или владение потеряно: task_id=%s",
            task_id,
            extra={'event': 'task_result_dropped', 'task_id': task_id},
        )
        return

    logger.info(
        "Обработка завершена успешно: task_id=%s, celery_task_id=%s",
        task_id, celery_task_id,
        extra={'event': 'task_processing_done', 'task_id': task_id},
    )

async def calculate_result(
    text: str
) -> tuple[int, int]:
    """Обработка текста."""
    logger.info('Запускаем обработку текста: считаем длину текста и количество слов')
    found = [
        word for word in FORBIDDEN_WORD_IN_TEXT if word in text.lower()
    ]
    if found:
        raise ForbiddenWordsError(found)
        
    original_length = len(text)
    chunks = text.split('\n')
    word_count = 0

    for i, chunk in enumerate(chunks):
        await asyncio.sleep(TIME_CELERY_TASK)
        word = chunk.split()
        word_count += len(word)


    return original_length, word_count


@celery.task(name='worker.sweep_stale_cancelling')
def sweep_stale_cancelling():
    asyncio.run(async_sweep_stale_cancelling())

async def async_sweep_stale_cancelling():
    async with get_session() as session:
        repo = TaskRepository(session)
        tasks_ids = await repo.sweep_stale_cancellations()  
        if tasks_ids:    
            logger.warning(
                'Sweep: переведены в CANCELLED задачи, зависшие в CANCELLING: ids=%s', tasks_ids
            )


@celery.task(
    bind=True,
    name='worker.get_file',
    acks_late=True,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_backoff_max=RETRY_BACKOFF_MAX,
    max_retries=MAX_TRIES,
    retry_jitter=True
)
async def get_file(self, task_id: int, internal_name: str) -> None:
    upload_dir = os.getenv("UPLOAD_DIR", "/app/files")
    file_path = Path(upload_dir) / internal_name
    if not file_path.exists():
        return {'status': 'failed', 'error': 'Файл не найден'}
    try:
        await asyncio.sleep(1)
        logger.info(
            "Воркер получил файл: task_id=%s, path=%s",
            task_id, file_path,
            extra={"event": "file_received_by_worker", "task_id": task_id},
        )
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}
