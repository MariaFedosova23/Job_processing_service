import logging
import asyncio
import os
from pathlib import Path
from sqlalchemy.exc import OperationalError
import uuid

from celery.exceptions import SoftTimeLimitExceeded


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
    CELERY_TASK_PROCESS_NAME,
    CELERY_TASK_GET_FILE_NAME
)
from src.services.task_service import TaskService
from src.services.exceptions import ForbiddenWordsError, TaskProcessingError
from src.enums import TaskOutcome

logger = logging.getLogger('job_processing_service')


@celery.task(
    bind=True,
    name=CELERY_TASK_PROCESS_NAME,
    acks_late=True,
    autoretry_for=(OperationalError, TimeoutError, ConnectionError),
    retry_backoff=True,
    retry_backoff_max=RETRY_BACKOFF_MAX,
    max_retries=MAX_TRIES,
    retry_jitter=True,
    soft_time_limit=SOFT_TIME,
    time_limit=TIME_LIMIT,
)
def process_task(self, task_id: int, run_id: str) -> str:
    is_final_attempt = self.request.retries >= self.max_retries
    celery_task_id = self.request.id
    
    outcome = asyncio.run(
        process_task_async(
            task_id,
            run_id=run_id,
            celery_task_id=celery_task_id,
            attempt=self.request.retries,
            is_final_attempt=is_final_attempt,
        )
    )
    return outcome.value


async def process_task_async(
        task_id: int,
        run_id: str,
        celery_task_id: str,
        attempt: int = 0,
        is_final_attempt: bool = False,
        
) -> TaskOutcome:
    owner_token: str | None = None
    try:
        logger.info(
            "Начало обработки задачи: task_id=%s, celery_task_id=%s",
            task_id, celery_task_id,
            extra={'event': 'task_processing_started', 'task_id': task_id},
        )
        owner_token = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        claim_started = loop.time()
        try:
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
                    return TaskOutcome.SKIPPED

                text = task.text

        except OperationalError:
            logger.warning(
                'БД недоступна на этапе захвата: task_id=%s', task_id
            )
            raise
            

        try:
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
            cancelled = await safe_confirm_cancellation(
                task_id,
                owner_token=owner_token,
            )
            if cancelled:
                logger.info(
                    "Задача отменена и подтверждена: task_id=%s",
                    task_id,
                    extra={'event': 'task_cancelled', 'task_id': task_id},
                )
                return TaskOutcome.CANCELLED
            else:
                logger.warning(
                    "Обработка прекращена: владение потеряно: task_id=%s",
                    task_id,
                    extra={'event': 'task_result_dropped', 'task_id': task_id},
                )
            return TaskOutcome.SKIPPED
            

        except ForbiddenWordsError as exc:
            logger.warning(
                "Бизнес-ошибка обработки: task_id=%s, error=%s",
                task_id, exc,
                extra={
                    'event': 'task_processing_business_error',
                    'task_id': task_id
                    
                },
            )
            await save_fail(
                task_id,
                owner_token=owner_token,
                error=str(exc)
            )
            return TaskOutcome.REJECTED
        

        except (TimeoutError, ConnectionError) as exc:
            logger.warning(
                'Временный сбой: task_id=%s, error=%s', task_id, exc
            )
            await safe_release(
                task_id, owner_token
            )
            raise

        
        except Exception as exc:
            logger.exception(
                'Непредвиденная ошибка во время вычисления: task_id=%s',
                task_id,
                extra={
                    'event': 'task_compute_unexpected_error',
                    'task_id': task_id
                },
            )
            await save_fail(task_id, owner_token, f'Внутренняя ошибка: {type(exc).__name__}')
            raise


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
                        'event': 'task_retries_exhausted',
                        'task_id': task_id
                    },

                )
                await save_fail(
                    task_id, owner_token, 'БД недоступна после всех попыток'
                )
                raise

            await safe_release(task_id, owner_token)
            raise

        except TaskProcessingError as exc:
            logger.warning(
                "Бизнес-ошибка обработки: task_id=%s, error=%s",
                task_id, exc,
                extra={
                    'event': 'task_processing_business_error',
                    'task_id': task_id
                },
            )
            await save_fail(
                task_id,
                owner_token=owner_token,
                error=str(exc)
            )
            return TaskOutcome.REJECTED


        except Exception as exc:
            logger.exception(
                'Непредвиденная ошибка обработки: task_id=%s, celery_task_id=%s',
                task_id, celery_task_id,
                extra={
                    'event': 'task_processing_unexpected_error', 'task_id': task_id
                },
            )
            await save_fail(
                task_id,
                owner_token=owner_token,
                error=f'Внутренняя ошибка: {type(exc).__name__}',
            )
            raise
        
        if saved is None:
            logger.warning(
                'Не удалось сохранить результат — lease истёк или владение потеряно: task_id=%s',
                task_id,
                extra={'event': 'task_result_dropped', 'task_id': task_id},
            )
            return TaskOutcome.SKIPPED

        logger.info(
            "Обработка завершена успешно: task_id=%s, celery_task_id=%s",
            task_id, celery_task_id,
            extra={'event': 'task_processing_done', 'task_id': task_id},
        )
        return TaskOutcome.DONE
    
    except SoftTimeLimitExceeded:
        if owner_token is not None:
            try: 
                await save_fail(task_id, owner_token, 'Превышено время обработки')
            except Exception:
                logger.exception('Не удалось записать ERROR при таймауте: task_id=%s', task_id)
        raise
    

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

    for chunk in chunks:
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

async def save_fail(task_id, owner_token, error):
    try:
        async with get_session() as session:
            service = TaskService(TaskRepository(session))
            await service.fail_processing(
                task_id,
                owner_token=owner_token,
                error=error,
            )
    except Exception:
        logger.exception(
            'Не удалось выставить ERROR: task_id=%s', task_id
        )
async def safe_release(task_id, owner_token):
    try:
        async with get_session() as session:
            service = TaskService(TaskRepository(session))
            await service.release_for_retry(
                task_id, owner_token=owner_token
            )
    except Exception:
        logger.exception(
            'Не удалось освободить задачу для ретрая : task_id=%s', task_id
        )

async def safe_confirm_cancellation(task_id, owner_token):
    try:
        async with get_session() as session:
            repo = TaskRepository(session)
            return await repo.confirm_cancellation(
                task_id,
                owner_token=owner_token,
            )
    except Exception:
        logger.exception(
            'Не удалось подтвердить отмену задачи : task_id=%s', task_id
        )

@celery.task(
    bind=True,
    name=CELERY_TASK_GET_FILE_NAME,
    acks_late=True,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_backoff_max=RETRY_BACKOFF_MAX,
    max_retries=MAX_TRIES,
    retry_jitter=True
)
def get_file(self, task_id, internal_name):
    return asyncio.run(
        get_file_async(task_id, internal_name)
    )


async def get_file_async(task_id: int, internal_name: str) -> dict | None:
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






                                  