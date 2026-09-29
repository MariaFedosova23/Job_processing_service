from src.worker.tasks.tasks import process_task, get_file


def enqueue_process_task(task_id: int) -> None:
    result = process_task.delay(task_id)
    return result.id


def enequeu_get_file() -> None:
    get_file.delay()
    return None