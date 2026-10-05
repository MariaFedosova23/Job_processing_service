import logging

from src.constants import (
    ALLOWED_STATUS_TRANSITIONS,
    API_PATCH_TRANSITIONS,
    WORKER_TRANSITIONS,
)
from src.enums import Status, Caller
from src.services.exceptions import (
    InvalidStatusTransitionError, TaskCannotBeProcessedError,
    TaskCannotBeCancelledError, TaskCannotBeRetryError
)

logger = logging.getLogger('job_processing_service')


ALLOWED_BY_CALLER: dict[Caller, dict[str, set[str]]] = {
    Caller.API_USER: API_PATCH_TRANSITIONS,
    Caller.WORKER: WORKER_TRANSITIONS,
}

def validate_transition_for_caller(
    task_id: int,
    old_status: Status,
    new_status: Status,
    caller: Caller
) -> None:
    """Проверяет, разрешен ли переход (old_status -> new_status)
    данному caller.
    """
    allowed_for_caller = ALLOWED_BY_CALLER.get(caller)
    if allowed_for_caller is None:
        raise TrasitionForbiddenError(
            task_id, old_status, new_status, caller
        )
    allowed = allowed_for_caller.get(old_status.value, set())
    if new_status.value not in allowed:
        logger.warning(
            'Недопустимый переход статуса: %s -> %s',
            old_status, new_status,
            extra={'event': 'task_status_change_failed', 'task_id': task_id},
        )
        raise TrasitionForbiddenError(
            task_id, old_status, new_status, caller
        )

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


CANCELLABLE_STATUSES = {Status.NEW, Status.QUEUED, Status.PROCESSING}

def validate_task_can_be_cancelled(task_id: int, current_status: str) -> None:
    """Проверяет, можно ли отменить задачу."""
    if current_status not in CANCELLABLE_STATUSES:
        logger.warning(
            'Отмена возможна только из %s: status=%s',
            CANCELLABLE_STATUSES, current_status,
            extra={"event": "task_cannot_be_cancelled", "task_id": task_id},
        )
        
        raise TaskCannotBeCancelledError(task_id, current_status)


