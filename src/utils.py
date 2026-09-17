import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


from src.models.task import TaskDB


logger = logging.getLogger('job_processing_service')


async def unique_external_id(
        external_id: str,
        db: AsyncSession
) -> None:
    result = await db.execute(
        select(TaskDB).where(TaskDB.external_id == external_id)
    )
    task = result.scalar_one_or_none()

    if task:
        logger.warning(
            "external_id уже существует: external_id=%s",
            external_id,
            extra={
                "event": "task_create_failed",
                "external_id": task.external_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='внешний идентификатор должен быть уникальным'
        )