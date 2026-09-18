import logging

from fastapi import Query, APIRouter, BackgroundTasks

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
from src.api.v1.dependencies import TaskServiceDep
from src.services.task_service import TaskService

logger = logging.getLogger('job_processing_service')

router = APIRouter(prefix='/api/v1/tasks', tags=['Задания'])


@router.get(
        path='',
        response_model=list[TaskResponseSchema],
        summary='Получить список заданий',
)
async def get_tasks(
    service: TaskServiceDep,
    status: Status | None = Query(
        None, description='Фильтр по статусу задания'
    ),
    priority: int | None = Query(
        None, ge=TASK_PRIORITY_LOW, le=TASK_PRIORITY_HIGH
    ),
    limit: int = Query(DEFAULT_LIMIT, ge=MIN_LIMIT, le=MAX_LIMIT),
    offset: int = Query(DEFAULT_OFFSET, ge=MIN_OFFSET),
) -> list[TaskResponseSchema]:

    return await service.list_tasks(
        status=status, priority=priority, limit=limit, offset=offset
    )


@router.get(
        path='/{task_id}',
        response_model=TaskResponseSchema,
        summary='Получить задание',
)
async def get_task(
    service: TaskServiceDep,
    task_id: int
) -> TaskResponseSchema:
    return await service.get_or_raise(task_id)


@router.post(
        path='',
        response_model=ShortResponseSchema,
        summary='Создать задание',
)
async def create_task(
    service: TaskServiceDep,
    task: TaskCreateSchema
) -> ShortResponseSchema:
    return await service.create(task)

    
@router.patch(
        path='/{task_id}/status',
        response_model=TaskResponseSchema,
        summary='Изменить статус задание',
)
async def patch_status_of_task(
    payload: TaskStatusSchema,
    task_id: int,
    service: TaskServiceDep
) -> TaskResponseSchema:
    return await service.change_status(task_id, payload.status)
    
   
@router.delete(
    '/{task_id}',
    summary='Удаление задачи',
)
async def delete_task(
    task_id: int,
    service: TaskServiceDep
):
    await service.delete(task_id)
    


@router.post(
    '/{task_id}/process',
    summary='Обработка задания',
    response_model=TaskResponseSchema
)
async def process_task(
    task_id: int,
    service: TaskServiceDep,
    background_task: BackgroundTasks
):
    task = await service.start_processing(task_id)
    
    background_task.add_task(
        TaskService.process, task_id, delay=TIME_BACKGROUND_TASK
    )
    return task
