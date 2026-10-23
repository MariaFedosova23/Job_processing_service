import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.services.exceptions import (
    DomainError,
    DuplicateExternalIdError,
    InvalidStatusTransitionError,
    TaskCannotBeProcessedError,
    TaskNotFoundError,
    TaskCannotBeCancelledError,
    TransitionForbiddenError,
    TaskStateConflictError,
    InvalidFileTypeError,
    FileTooLargeError,
    AccessDenied,
    InvalidCredentials,
    UserInactive,
    UserNotFound,
    UserAlreadyExists,
    WrongPassword,
    InvalidPassword,
    InvalidUsername,
)

logger = logging.getLogger('job_processing_service')


async def invalid_username(request: Request, exc: InvalidPassword):
    logger.warning(
        "В username ошибки",
        extra={"event": "invalid_username"},
    )
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def invalid_password(request: Request, exc: InvalidPassword):
    logger.warning(
        "В пароле ошибки",
        extra={"event": "invalid_password"},
    )
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def password_not_found_user(request: Request, exc: WrongPassword):
    logger.warning(
        "Пароль не найден",
        extra={"event": "password_not_found", "user_id": exc.user_id},
    )
    return JSONResponse(status_code=403, content={"detail": str(exc)})

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


async def cannot_cancell_handler(
    request: Request, exc: TaskCannotBeCancelledError,
):
    logger.warning(
        "Задачу нельзя обработать",
        extra={
            "event": "task_cannot_be_cancelled",
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

async def forbidden_handler(request: Request, exc: TransitionForbiddenError):
    return JSONResponse(
        status_code=403,
        content={
            "detail": str(exc),
            "task_id": exc.task_id,
            "old_status": str(exc.old_status),
            "new_status": str(exc.new_status),
            "caller": str(exc.caller),
        },
    )

async def conflict_handler(request: Request, exc: TaskStateConflictError):
    return JSONResponse(
        status_code=409,
        content={
            "detail": str(exc),
            "task_id": exc.task_id,
            "expected_status": str(exc.expected_status),
        },
    )

async def handle_invalid_file_type(
    request: Request, exc: InvalidFileTypeError
) -> JSONResponse:
    logger.warning(
        'Неподдерживаемый тип файла: content_type=%s',
        exc.content_type,
        extra={'event': 'invalid_file_type'},
    )
    return JSONResponse(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        content={
            "detail": str(exc),
            "content_type": exc.content_type,
        },
    )


async def handle_file_too_large(
    request: Request, exc: FileTooLargeError
) -> JSONResponse:
    logger.warning(
        'Файл превышает лимит: size=%s, limit=%s',
        exc.size, exc.limit,
        extra={'event': 'file_too_large'},
    )
    return JSONResponse(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        content={
            "detail": str(exc),
            "size": exc.size,
            "limit": exc.limit,
        },
    )

async def user_exists(
    request: Request, exc: UserAlreadyExists
):
    return JSONResponse(status_code=409, content={'detail': str(exc)})

async def user_not_found(_: Request, exc: UserNotFound):
    return JSONResponse(status_code=401, content={"detail": str(exc)})


async def invalid_credentials(_: Request, exc: InvalidCredentials):
    return JSONResponse(status_code=401, content={"detail": "Неверные учётные данные"})

async def user_inactive(_: Request, exc: UserInactive):
    return JSONResponse(status_code=403, content={"detail": "Аккаунт деактивирован"})

async def access_denied(_: Request, exc: AccessDenied):
    return JSONResponse(status_code=403, content={"detail": "Доступ запрещён"})


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрирует все обработчики доменных исключений."""
    app.add_exception_handler(InvalidUsername, invalid_username)
    app.add_exception_handler(InvalidPassword, invalid_password)
    app.add_exception_handler(WrongPassword, password_not_found_user)
    app.add_exception_handler(UserAlreadyExists, user_exists)
    app.add_exception_handler(AccessDenied, access_denied)
    app.add_exception_handler(UserInactive, user_inactive)
    app.add_exception_handler(InvalidCredentials, invalid_credentials)
    app.add_exception_handler(UserNotFound, user_not_found)
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
    app.add_exception_handler(
            TaskCannotBeCancelledError, cannot_cancell_handler,
    )
    app.add_exception_handler(DomainError, domain_error_handler)

    app.add_exception_handler(
        TransitionForbiddenError, forbidden_handler
    )
    app.add_exception_handler(
        TaskStateConflictError, conflict_handler
    )
    app.add_exception_handler(InvalidFileTypeError, handle_invalid_file_type)
    app.add_exception_handler(FileTooLargeError, handle_file_too_large)





