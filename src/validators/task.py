import logging

from fastapi import HTTPException, status

from src.constants import ALLOWED_STATUS_TRANSITIONS
from src.schemas.tasks import Status

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
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f'Нельзя перевести задачу из "{old_status}" в "{new_status}". '
                f'Допустимые: {sorted(allowed)}'
            ),
        )


def validate_task_can_be_processed(task_id: int, current_status: str) -> None:
    """Проверяет, что задачу можно запустить в обработку."""
    if current_status != Status.NEW:
        logger.warning(
            'Задание нельзя обработать: status=%s',
            current_status,
            extra={'event': 'task_processing_failed', 'task_id': task_id},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Задание нельзя обработать',
        )