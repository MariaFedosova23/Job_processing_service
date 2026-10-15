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
    asyncio.run(async_relay_outbox())

def _backoff(attempts: int) -> timedelta:
    seconds = min(2 ** attempts, OUTBOX_BACKOFF_CAP_SECONDS)
    return timedelta(seconds=seconds)

async def async_relay_outbox() -> None:
    async with get_session() as session:
        repo = OutboxRepository(session)

        async with session.begin():
            rows = await repo.lock_pending_batch(limit=OUTBOX_BATCH_SIZE)
            if not rows:
                return
            now = datetime.now(timezone.utc)
            sent_count = 0
            failed_count = 0
            for row in rows:
                try:
                    celery.send_task(
                        row.task_name,
                        kwargs=row.payload,
                        # task_id=row.payload.get('run_id')
                    )
                except Exception as exc:
                    row.attempts += 1
                    row.last_error = str(exc)

                    if row.attempts >= OUTBOX_MAX_ATTEMPTS:
                        row.status = OutboxStatus.FAILED
                        failed_count += 1
                        logger.error(
                            'Outbox: исчерпаны попытки: id=%s, task_id=%s, attempts=%s',
                            row.id, row.payload.get('task_id'), row.attempts,
                            extra={'event': 'outbox_failed', 'outbox_id': row.id},
                        )
                    else:
                        row.next_retry_at = now + _backoff(row.attempts)
                        logger.warning(
                            'Outbox: повтор через %ss: id=%s, attempts=%s, error=%s',
                            row.id, row.attempts, exc,
                            extra={'event': 'outbox_retry', 'outbox_id': row.id},
                        )
                else:
                    row.status = OutboxStatus.SENT
                    row.sent_at = datetime.now()
                    row.last_error = None
                    sent_count += 1

            if sent_count or failed_count:
                logger.info(
                    'Relay: обработано %s (sent=%s, failed=%s)',
                    len(rows), sent_count, failed_count,
                    extra={'event': 'outbox_relay_batch'},
                )