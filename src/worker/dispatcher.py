from src.worker.tasks.tasks import process_task


def enqueue_process_task(task_id: int) -> None:
    task = process_task.delay(task_id)
    return 
    