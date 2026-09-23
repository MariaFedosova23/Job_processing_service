from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, ConfigDict

from src.constants import (
    TASK_PRIORITY_DEFAULT, TASK_PRIORITY_HIGH, TASK_PRIORITY_LOW,
    TASK_TEXT_MIN_LENGTH, TASK_TITLE_MAX_LENGTH, TASK_TITLE_MIN_LENGTH
)
from src.enums import Status




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


class ShortResponseSchema(TaskStatusSchema):
    id: int


class TaskResponseSchema(TaskCreateSchema, ShortResponseSchema):
    created_at: datetime
    updated_at: datetime

class TaskResponseProcessSchema(ShortResponseSchema):
    celery_task_id: str
