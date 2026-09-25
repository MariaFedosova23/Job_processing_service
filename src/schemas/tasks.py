from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, ConfigDict

from src.constants import (
    TASK_PRIORITY_DEFAULT, TASK_PRIORITY_HIGH, TASK_PRIORITY_LOW,
    TASK_TEXT_MIN_LENGTH, TASK_TITLE_MAX_LENGTH, TASK_TITLE_MIN_LENGTH
)
from src.enums import Status


# input data

class TaskCreateSchema(BaseModel):

    external_id: str
    title: str = Field(
        min_length=TASK_TITLE_MIN_LENGTH, max_length=TASK_TITLE_MAX_LENGTH
    )
    text: str = Field(min_length=TASK_TEXT_MIN_LENGTH)
    priority: Annotated[
        int,
        Field(
            ge=TASK_PRIORITY_LOW,
            le=TASK_PRIORITY_HIGH,
            default=TASK_PRIORITY_DEFAULT
        )
    ]

    model_config = ConfigDict(extra='forbid')


class TaskStatusSchema(BaseModel):
    status: Status = Status.NEW


# output data

class TaskResultSchema(BaseModel):
    """Вложенная схема для result."""
    original_length: int
    word_count: int
    processed_at: datetime

class TaskShortSchema(BaseModel):
    id: int
    status: Status


class TaskListSchema(BaseModel):
    """Элемент списка GET /tasks."""
    id: int
    external_id: str
    title: str
    priority: int
    status: Status
    created_at: datetime

class TaskDetailSchema(TaskListSchema):
    pass

class TaskDetailStateSchema(BaseModel):
    """Детальный ответ: GET /tasks/{id}, PATCH, process."""
    id: int
    status: Status
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    result: TaskResultSchema | None
    error: str | None

class TaskResponseProcessSchema(BaseModel):
    id: int
    status: Status
    celery_task_id: str



