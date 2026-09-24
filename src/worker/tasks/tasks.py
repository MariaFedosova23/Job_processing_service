import asyncio
from datetime import datetime, timezone
import time
from asyncio import sleep


from sqlalchemy.exc import OperationalError
from src.worker.app import celery
from src.database.database import get_session
from src.database.models.task import TaskDB, TaskResultDB
from src.database.repositories.task import TaskRepository
from src.enums import Status
# from src.worker.tasks.base_task import DatabaseTask
from src.constants import MAX_TRIES, RETRY_BACKOFF_MAX, TIME_CELERY_TASK

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
        repo = TaskRepository(session)
        task = await repo.mark_processing(
            task_id,
            started_at=datetime.now(timezone.utc)
        )
        if task is None:
            return
        
        text = task.text

    try: 
        original_length = len(text)
        word_count = len(text.split())
        now = datetime.now(timezone.utc)

        async with get_session() as session:
            repo = TaskRepository(session)
            await repo.save_result_and_complete(
                task_id,
                original_length=original_length,
                word_count=word_count,
                processed_at=now,
                finished_at=now,
            )
            sleep()
            

    except Exception as exc:
        async with get_session() as session:
            repo = TaskRepository(session)
            await repo.mark_failed(
                task_id,
                error=str(exc),
                finished_at=datetime.now(timezone.utc),
            )
        raise



    




