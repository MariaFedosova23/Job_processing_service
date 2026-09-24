import asyncio
from celery.signals import worker_process_init
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
    task_acks_late=True,
    result_expires=3600
    # task_routes=TASK_ROUTES,
)


@worker_process_init.connect
def init_worker_process(**kwargs) -> None:
    from src.database.database import engine_worker

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(engine_worker.dispose())
    except:
        pass
    
