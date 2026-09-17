import logging

from fastapi import HTTPException, status
from asyncio import sleep
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import AsyncSessionLocal
from src.models.task import TaskDB
from src.schemas.tasks import Status

logger = logging.getLogger('job_processing_service')


async def process(task_id: int, delay: int) -> None:
    await sleep(delay)
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(TaskDB).where(TaskDB.id == task_id)
            )
            task = result.scalar_one_or_none()
            if task is None:
                logger.warning(
                    'Задача исчезла во время обработки: task_id=%s',
                    task_id,
                    extra={'event': 'task_not_found', 'task_id': task_id},
                )
                return

            task.status = Status.DONE
            await session.commit()
            logger.info(
                'Задача обработана: task_id=%s',
                task_id,
                extra={'event': 'task_processing_done', 'task_id': task_id},
            )
        except Exception:
            await session.rollback()
            logger.exception(
                'Ошибка при фоновой обработке: task_id=%s',
                task_id,
                extra={'event': 'task_processing_failed', 'task_id': task_id},
            )


async def get_task_or_404(
    db: AsyncSession,
    task_id: int,
    *,
    event: str = 'task_not_found',
) -> TaskDB:
    result = await db.execute(
        select(TaskDB).where(TaskDB.id == task_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        logger.warning(
            'Задача не найдена',
            extra={'event': event, 'task_id': task_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Задание не найдено',
        )
    return task


async def set_task_status(
    db: AsyncSession,
    task: TaskDB,
    new_status: str,
    *,
    error_detail: str = 'Не удалось изменить статус',
    event: str = 'task_status_changed',
) -> TaskDB:
    old_status = task.status
    try:
        task.status = new_status
        await db.commit()
        await db.refresh(task)
    except Exception:
        await db.rollback()
        logger.exception(
            'Ошибка БД при смене статуса: %s -> %s',
            old_status, new_status,
            extra={'event': 'db_error', 'task_id': task.id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail,
        )
    logger.info(
        'Статус задачи изменён: %s -> %s',
        old_status, new_status,
        extra={'event': event, 'task_id': task.id},
    )
    return task