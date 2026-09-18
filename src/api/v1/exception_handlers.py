import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.services.exceptions import (
    DomainError,
    DuplicateExternalIdError,
    InvalidStatusTransitionError,
    TaskCannotBeProcessedError,
    TaskNotFoundError,
)

logger = logging.getLogger("job_processing_service")


async def task_not_found_handler(request: Request, exc: TaskNotFoundError):
    logger.warning(
        "Задача не найдена",
        extra={"event": "task_not_found", "task_id": exc.task_id},
    )
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def duplicate_external_id_handler(
    request: Request, exc: DuplicateExternalIdError,
):
    logger.warning(
        "Дубликат external_id",
        extra={"event": "task_duplicate", "external_id": exc.external_id},
    )
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def invalid_status_transition_handler(
    request: Request, exc: InvalidStatusTransitionError,
):
    logger.warning(
        "Недопустимый переход статуса",
        extra={
            "event": "invalid_status_transition",
            "task_id": exc.task_id,
            "old_status": exc.old_status,
            "new_status": exc.new_status,
        },
    )
    return JSONResponse(status_code=422, content={"detail": str(exc)})


async def cannot_process_handler(
    request: Request, exc: TaskCannotBeProcessedError,
):
    logger.warning(
        "Задачу нельзя обработать",
        extra={
            "event": "task_cannot_be_processed",
            "task_id": exc.task_id,
            "status": exc.status,
        },
    )
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def domain_error_handler(request: Request, exc: DomainError):
    logger.warning(
        "Доменная ошибка",
        extra={"event": "domain_error", "error": type(exc).__name__},
    )
    return JSONResponse(status_code=400, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрирует все обработчики доменных исключений."""
    app.add_exception_handler(TaskNotFoundError, task_not_found_handler)
    app.add_exception_handler(
        DuplicateExternalIdError, duplicate_external_id_handler,
    )
    app.add_exception_handler(
        InvalidStatusTransitionError, invalid_status_transition_handler,
    )
    app.add_exception_handler(
        TaskCannotBeProcessedError, cannot_process_handler,
    )
    app.add_exception_handler(DomainError, domain_error_handler)