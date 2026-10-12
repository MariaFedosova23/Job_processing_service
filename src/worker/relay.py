import asyncio
import logging
from datetime import datetime, timedelta, timezone

from src.worker.app import celery
from src.constants import (
    OUTBOX_BATCH_SIZE,
    OUTBOX_MAX_ATTEMPTS,
    OUTBOX_BACKOFF_CAP_SECONDS,
)
from src.database.repositories.outbox import OutboxRepository
from src.database.database import get_session
from src.enums import OutboxStatus

logger = logging.getLogger('job_processing_service')

@celery.task(name='worker.relay_outbox')
def relay_outbox() -> None:
    asyncio.run(_async_relay_outbox())

def _backoff(attempts: int) -> timedela:
    seconds = min(2 ** attempts, OUTBOX_BACKOFF_CAP_SECONDS)
    return timedelta(seconds=seconds)

async def _async_relay_outbox() -> None:
    async with get_session() as session:
        repo = OutboxRepository(session)

        async with session.begin():
            rows = await repo.lock_pending_batch(limit=OUTBOX_BATCH_SIZE)
            if not rows:
                return
            sent_count = 0
            failed_count = 0
            for row in rows:
                celery.send_task(
                    row.task_name,
                    kwargs=row.payload,
                    task_id=row.payload.get('run_id')
                )