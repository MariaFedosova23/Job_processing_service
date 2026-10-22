import logging

from fastapi import Query, APIRouter, UploadFile, File, Depends
from authx import TokenPayload

from src.schemas.tasks import (
    TaskCreateSchema,
    TaskShortSchema,
    TaskListSchema,
    TaskDetailStateSchema,
    TaskResponseProcessSchema,
    TaskDetailSchema,
    TaskStatusUpdateSchema,
)
from src.constants import (
    DEFAULT_LIMIT, DEFAULT_OFFSET,
    MIN_LIMIT, MIN_OFFSET, MAX_LIMIT,
    TASK_PRIORITY_HIGH,
    TASK_PRIORITY_LOW,
)
from src.api.v1.dependencies import (
    TaskServiceDep, FileServiceDep, require_scopes, get_task_for_action
    
)
from src.config import security
from src.enums import Status, Caller
from src.schemas.file import FileResponse
# from src.auth.dependencies import get_current_user, require_scopes
from src.database.models.task import TaskDB

logger = logging.getLogger('job_processing_service')

router = APIRouter(prefix='/api/v1/tasks', tags=['tasks'])


@router.get(
        path='',
        response_model=list[TaskListSchema],
        summary='Получить список заданий',
        dependencies=[Depends(require_scopes(
        'tasks:read', 'tasks:read_own', all_required=False
    ))]
)
async def get_tasks(
    service: TaskServiceDep,
    payload: TokenPayload = Depends(security.access_token_required),
    status: Status | None = Query(
        None, description='Фильтр по статусу задания'
    ),
    priority: int | None = Query(
        None, ge=TASK_PRIORITY_LOW, le=TASK_PRIORITY_HIGH
    ),
    limit: int = Query(DEFAULT_LIMIT, ge=MIN_LIMIT, le=MAX_LIMIT),
    offset: int = Query(DEFAULT_OFFSET, ge=MIN_OFFSET),
) -> list[TaskListSchema]:
    return await service.list_tasks(
        user_id=int(payload.sub),
        can_access_any=payload.has_scopes('tasks:read'),
        status=status, priority=priority, limit=limit, offset=offset
    )
    


@router.get(
    path='/{task_id}',
    response_model=TaskDetailStateSchema,
    summary='Получить задание',
    dependencies=[Depends(
        require_scopes(
            'tasks:read', 'tasks:read_own', all_required=False)
        )
    ]
)
async def get_task(
    task: TaskDB = Depends(get_task_for_action('tasks:read', 'tasks:read_own')),
) -> TaskDetailStateSchema:
    return task


@router.post(
        path='',
        response_model=TaskShortSchema,
        summary='Создать задание',
        dependencies=[Depends(require_scopes('tasks:create'))],
)
async def create_task(
    service: TaskServiceDep,
    task: TaskCreateSchema,
    payload: TokenPayload = Depends(security.access_token_required),
) -> TaskShortSchema:
    return await service.create(task, owner_id=int(payload.sub))

    
@router.patch(
        path='/{task_id}/status',
        response_model=TaskDetailSchema,
        summary='Изменить статус задание',
        dependencies=[Depends(require_scopes('tasks:patch_status', 'tasks:patch_own_status', all_required=False))],
)
async def patch_status_of_task(
    payload: TaskStatusUpdateSchema,
    service: TaskServiceDep,
    task: TaskDB = Depends(get_task_for_action('tasks:patch_status', 'tasks:patch_own_status')),
) -> TaskDetailSchema:
    return await service.change_status(
        task.id,
        expected_status=payload.expected_status,
        new_status=payload.status,
        caller=Caller.API_USER,
    )
    
@router.delete(
    '/{task_id}',
    summary='Удаление задачи',
    dependencies=[Depends(
        require_scopes(
        'tasks:delete', 'tasks:delete_own', all_required=False)
        )
    ]
)
async def delete_task(
    service: TaskServiceDep,
    task: TaskDB = Depends(get_task_for_action('tasks:delete', 'tasks:delete_own')),
):
    await service.delete(task.id)
    
@router.post(
    '/{task_id}/process',
    summary='Обработка задания',
    response_model=TaskResponseProcessSchema,
    dependencies=[Depends(
        require_scopes(
        'tasks:process', 'tasks:process_own', all_required=False)
        )
    ]
)
async def process_task(
    # task_id: int,
    service: TaskServiceDep,
    task: TaskDB = Depends(get_task_for_action('tasks:process', 'tasks:process_own')),
):
    result = await service.start_processing(task.id)
    return TaskResponseProcessSchema(
        id=result.task.id,
        status=result.task.status,
        run_id=result.run_id,
    )

@router.post(
    '/{task_id}/retry',
    summary='Повторный запуск ошибочного задания',
    response_model=TaskResponseProcessSchema,
    dependencies=[Depends(
        require_scopes(
        'tasks:retry', 'tasks:retry_own', all_required=False)
        )
    ]
)
async def retry_process_task(
    # task_id: int,
    service: TaskServiceDep,
    task: TaskDB = Depends(get_task_for_action('tasks:retry', 'tasks:retry_own')),
):
    result = await service.retry_task(task.id)
    return TaskResponseProcessSchema(
        id=result.task.id,
        status=result.task.status,
        run_id=result.run_id,
    )

@router.post(
    '/{task_id}/cancel',
    summary='отмена выполнения обрабоки задания',
    response_model=TaskDetailSchema,
    dependencies=[Depends(
        require_scopes(
        'tasks:cancel', 'tasks:cancel_own', all_required=False)
        )
    ]
)
async def cancel_process_task(
    # task_id: int,
    service: TaskServiceDep,
    task: TaskDB = Depends(get_task_for_action('tasks:cancel', 'tasks:cancel_own')),
):
    result = await service.cancel_task(task.id)
    return result

@router.post(
    '/{task_id}/files',
    summary='загрузка файла',
    response_model=FileResponse,
    dependencies=[Depends(
        require_scopes(
        'tasks:upload_file', 'tasks:upload_file_own', all_required=False)
        )
    ]
)
async def upload_file(
    # task_id: int,
    service: FileServiceDep,
    file: UploadFile = File(...),
    task: TaskDB = Depends(get_task_for_action('tasks:upload_file', 'tasks:upload_file_own')),
):
    content = await file.read()
    file_db = await service.upload_file(
        task_id=task.id,
        filename=file.filename,
        content_type=file.content_type,
        content=content,
    )
    return file_db
