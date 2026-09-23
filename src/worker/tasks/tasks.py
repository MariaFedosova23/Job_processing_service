import time
from src.worker.app import celery


@celery.task()
def process_task(task_id: int):
    time.sleep(15)
    return {'message': 'change queued -> processing'}

    
    