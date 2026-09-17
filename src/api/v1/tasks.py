import logging

from fastapi import HTTPException, status, Query, APIRouter, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy import select


from src.api.v1.dependencies import SessionDep
from src.models.task import TaskDB
from src.utils import unique_external_id
from src.schemas.tasks import (
    TaskCreateSchema, TaskResponseSchema,
    ShortResponseSchema, TaskStatusSchema,
    Status
)
from src.constants import (
    DEFAULT_LIMIT, DEFAULT_OFFSET,
    MIN_LIMIT, MIN_OFFSET, MAX_LIMIT,
    TASK_PRIORITY_HIGH,
    TASK_PRIORITY_LOW,
    TIME_BACKGROUND_TASK
)
from src.services.task_service import process, get_task_or_404, set_task_status
from src.validators.task import (
    validate_status_transition, validate_task_can_be_processed
)


logger = logging.getLogger('job_processing_service')

router = APIRouter()


@router.get(
        path='/api/v1/tasks',
        response_model=list[TaskResponseSchema],
        summary='Получить список заданий',
        tags=['Задания']
)
async def get_tasks(
    db: SessionDep,
    status: Status | None = Query(
        None, description='Фильтр по статусу задания'
    ),
    priority: int | None = Query(
        None, ge=TASK_PRIORITY_LOW, le=TASK_PRIORITY_HIGH
    ),
    limit: int = Query(DEFAULT_LIMIT, ge=MIN_LIMIT, le=MAX_LIMIT),
    offset: int = Query(DEFAULT_OFFSET, ge=MIN_OFFSET),
) -> list[TaskResponseSchema]:

    stmt = select(TaskDB)

    if status is not None:
        stmt = stmt.where(TaskDB.status == status)
    if priority is not None:
        stmt = stmt.where(TaskDB.priority == priority)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get(
        path='/api/v1/tasks/{task_id}',
        summary='Получить задание',
        tags=['Задания']
)
async def get_task(
    db: SessionDep,
    task_id: int
) -> TaskResponseSchema:
    return await get_task_or_404(db, task_id)


@router.post(
        path='/api/v1/tasks',
        response_model=ShortResponseSchema,
        summary='Создать задание',
        tags=['Задания']
)
async def create_task(
    db: SessionDep,
    task: TaskCreateSchema
) -> ShortResponseSchema:
    await unique_external_id(task.external_id, db)
    new_task = TaskDB(
        title=task.title,
        text=task.text,
        priority=task.priority,
        external_id=task.external_id
    )
    try:
        db.add(new_task)
        await db.commit()
        await db.refresh(new_task)
    except Exception:
        logger.exception(
            'Ошибка БД при создании задачи: external_id=%s',
            task.external_id,
            extra={
                'event': 'db_error',
            },
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Не удалось создать задачу',
        )
    logger.info(
        'Задача создана: external_id=%s',
        task.external_id,
        extra={
            'event': "task_created",
            'task_id': new_task.id,
        },
    )
    return new_task


@router.patch(
        path='/api/v1/tasks/{task_id}/status',
        response_model=TaskResponseSchema,
        summary='Изменить статус задание',
        tags=['Задания']
)
async def patch_status_of_task(
    payload: TaskStatusSchema,
    task_id: int,
    db: SessionDep
) -> TaskResponseSchema:
    task_db = await get_task_or_404(
        db, task_id, event='task_status_change_failed'
    )
    old_status = task_db.status
    new_status = payload.status.value
    validate_status_transition(task_id, old_status, new_status)
    
    return await set_task_status(db, task_db, new_status)

   
@router.delete(
    '/api/v1/tasks/{task_id}',
    summary='Удаление задачи',
    tags=['Задания']
)
async def delete_task(
    task_id: int,
    db: SessionDep
):
    task = await get_task_or_404(db, task_id)
    try:
        await db.delete(task)
        await db.commit()
    except Exception:
        logger.exception(
            'Ошибка БД при удалении задачи: task_id=%s',
            task.id
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Не удалось удалить задачу',
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    '/api/v1/tasks/{task_id}/process',
    summary='Обработка задания',
    tags=['Задания'],
    response_model=TaskResponseSchema
)
async def process_task(
    task_id: int,
    db: SessionDep,
    background_task: BackgroundTasks
):
    task = await get_task_or_404(db, task_id)
    validate_task_can_be_processed(task_id, task.status)
    
    task = await set_task_status(
        db,
        task,
        Status.PROCESSING,
        error_detail='Не удалось запустить обработку',
    )
    
    background_task.add_task(
        process, task_id, delay=TIME_BACKGROUND_TASK
    )
    return task
