from src.worker.app import celery

from src.constants import CELERY_TASK_GET_FILE_NAME

def enequeue_get_file(task_id: int, internal_name: str) -> None:
    celery.send_task(
        CELERY_TASK_GET_FILE_NAME,
        kwargs={'task_id': task_id, 'internal_name': internal_name},
    )
   