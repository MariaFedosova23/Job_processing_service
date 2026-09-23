from celery import Celery

from src.worker.config import (
    ACCEPT_CONTENT,
    BROKER_URL,
    ENABLE_UTC,
    RESULT_BACKEND,
    RESULT_SERIALIZER,
    # TASK_ROUTES,
    TASK_SERIALIZER,
    TIMEZONE,
)

celery = Celery(
    'worker',
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=['src.worker.tasks.tasks'],
)

celery.conf.update(
    task_serializer=TASK_SERIALIZER,
    result_serializer=RESULT_SERIALIZER,
    accept_content=ACCEPT_CONTENT,
    timezone=TIMEZONE,
    enable_utc=ENABLE_UTC,
    # task_routes=TASK_ROUTES,
)