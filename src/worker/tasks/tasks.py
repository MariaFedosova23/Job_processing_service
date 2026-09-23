import time
from src.worker.app import celery
from src.worker.tasks.base_task import DatabaseTask


@celery.task(
    base=DatabaseTask,
    bind=True,
    name='process_document'
)
def process_document(task_id: int):
    time.sleep(15)
    return {'message': 'change queued -> processing'}

    
    