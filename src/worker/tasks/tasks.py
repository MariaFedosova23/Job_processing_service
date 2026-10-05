import logging
import asyncio
import os
from pathlib import Path
from sqlalchemy.exc import OperationalError
import uuid
from src.worker.heartbeat import LeaseHeartbeat

from src.worker.app import celery
from src.database.database import get_session
from src.database.repositories.task import TaskRepository
from src.constants import (
    MAX_TRIES,
    RETRY_BACKOFF_MAX,
    TIME_CELERY_TASK,
    FORBIDDEN_WORD_IN_TEXT,
    LEASE_SECONDS
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
    retry_jitter=True
)
def process_task(self, task_id: int) -> None:
    is_final_attempt = self.request.retries >= self.max_retries
    celery_task_id = self.request.id

    asyncio.run(
        process_task_async(
            task_id,
            celery_task_id=celery_task_id,
            attempt=self.request.retries,
            is_final_attempt=is_final_attempt,
        )
    )


async def process_task_async(
        task_id: int,
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

    async with get_session() as session:
        service = TaskService(
            TaskRepository(session)
        )
        task = await service.begin_processing(
            task_id,
            allow_processing=attempt > 0,
            owner_token=owner_token,
            lease_seconds = LEASE_SECONDS
        )
        if task is None:
            return None
        text = task.text
        run_id = task.run_id

    heartbeat = LeaseHeartbeat(
        session_factory=get_session,
        task_id=task_id,
        owner_token=owner_token,
        lease_seconds=LEASE_SECONDS,
    )
    heartbeat.start()
    try:
        found = [
            word for word in FORBIDDEN_WORD_IN_TEXT if word in text.lower()
        ]
        if found:
            raise ForbiddenWordsError(found)
           
        original_length = len(text)
        word_count = len(text.split())
        
        await asyncio.sleep(TIME_CELERY_TASK)

        if heartbeat.is_lost:
            logger.warning(
                "Результат не сохраняем — lease потерян: task_id=%s",
                task_id,
                extra={"event": "task_result_dropped", "task_id": task_id},
            )
            return

            
        async with get_session() as session:
            service = TaskService(
                TaskRepository(session)
            )
            await service.complete_processing(
                task_id,
                owner_token=owner_token,
                original_length=original_length,
                word_count=word_count,
                run_id=run_id,
            )
        logger.info(
            "Обработка завершена успешно: task_id=%s, celery_task_id=%s",
            task_id, celery_task_id,
            extra={'event': 'task_processing_done', 'task_id': task_id},
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
            return None
        try:
            if not heartbeat.is_lost:
                async with get_session() as session:
                    service = TaskService(TaskRepository(session))
                    await service.release_for_retry(
                        task_id, owner_token=owner_token,
                    )
   
        except Exception:
            logger.exception(
                "Не удалось освободить задачу перед ретраем: task_id=%s",
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
        if not heartbeat.is_lost:
            async with get_session() as session:
                service = TaskService(
                    TaskRepository(session)
                )
                await service.fail_processing(
                    task_id,
                    owner_token=owner_token,
                    error=str(exc))

    except Exception as exc:
        logger.exception(
            'Непредвиденная ошибка обработки: task_id=%s, celery_task_id=%s',
            task_id, celery_task_id,
            extra={
                'event': 'task_processing_unexpected_error', 'task_id': task_id
            },
        )
        if not heartbeat.is_lost:
            async with get_session() as session:
                service = TaskService(
                    TaskRepository(session)
                )
                await service.fail_processing(
                    task_id,
                    owner_token=owner_token,
                    error=f'Внутренняя ошибка: {
                        type(exc).__name__
                    }',
                )
    finally:
        heartbeat.stop()


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
def get_file(self, task_id: int, internal_name: str) -> None:
    upload_dir = os.getenv("UPLOAD_DIR", "/app/files")
    file_path = Path(upload_dir) / internal_name
    if not file_path.exists():
        return {'status': 'failed', 'error': 'Файл не найден'}
    try:
        asyncio.sleep(1)  # обработка файла
        logger.info(
            "Воркер получил файл: task_id=%s, path=%s",
            task_id, file_path,
            extra={"event": "file_received_by_worker", "task_id": task_id},
        )
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}
