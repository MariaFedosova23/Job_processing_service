import logging

from src.constants import ALLOWED_STATUS_TRANSITIONS
from src.schemas.tasks import Status
from src.services.exceptions import (
    InvalidStatusTransitionError, TaskCannotBeProcessedError,
    TaskCannotBeCancelledError, TaskCannotBeRetryError
)

logger = logging.getLogger('job_processing_service')


def validate_status_transition(
    task_id: int,
    old_status: str,
    new_status: str,
) -> None:
    """Проверяет, допустим ли переход статуса. Бросает 422, если нет."""
    allowed = ALLOWED_STATUS_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        logger.warning(
            'Недопустимый переход статуса: %s -> %s',
            old_status, new_status,
            extra={'event': 'task_status_change_failed', 'task_id': task_id},
        )
        raise InvalidStatusTransitionError(task_id, old_status, new_status)


def validate_task_can_be_processed(task_id: int, current_status: str) -> None:
    """Проверяет, что задачу можно запустить в обработку."""
    if current_status != Status.NEW:
        logger.warning(
            'Задание нельзя обработать: status=%s',
            current_status,
            extra={'event': 'task_processing_failed', 'task_id': task_id},
        )
        raise TaskCannotBeProcessedError(task_id, current_status)


def validate_task_can_be_retry(task_id: int, current_status: str) -> None:
    """Проверяет, что ошибочную задачу можно запустить повторно."""
    if current_status != Status.ERROR:
        logger.warning(
            f'Задание можно повторно запустить '
            f'только при статусе {Status.ERROR}: status=%s',
            current_status,
            extra={'event': 'task_cannot_be_retied', 'task_id': task_id}
        )
        raise TaskCannotBeRetryError(task_id, current_status)


def validate_task_can_be_canclled(task_id: int, current_status: str) -> None:
    """Проверяет, можно ли отменить задачу."""
    if current_status not in (Status.QUEUED, Status.PROCESSING):
        logger.warning(
            f'Задание можно повторно запустить '
            f'только при статусе {Status.QUEUED} или '
            f'{Status.PROCESSING}: status=%s',
            current_status,
            extra={'event': 'task_cannot_be_cancelled', 'task_id': task_id}
        )
        raise TaskCannotBeCancelledError(task_id, current_status)


