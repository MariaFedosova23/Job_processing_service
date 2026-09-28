from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.task_service import TaskService, StartProcessingResult
from src.enums import Status
from src.services.exceptions import TaskNotFoundError, TaskCannotBeProcessedError


@pytest.fixture
def repo():
    repo = AsyncMock()
    return repo

@pytest.fixture
def service(repo):
    return TaskService(repo)

@pytest.fixture
def task_new():
    task = MagicMock()
    task.id = 1
    task.status = Status.NEW
    return task

async def test_start_processing_happy_path(service, repo, task_new):
    repo.get_with_result.return_value = task_new
    repo.update_status.return_value = task_new

    with patch.object(service, '_enqueue', return_value="celery-abc") as enqueue:
        result = await service.start_processing(task_id=1)

    assert isinstance(result, StartProcessingResult)
    assert result.task is task_new
    assert result.celery_task_id == "celery-abc"

    enqueue.assert_called_once_with(1)
    repo.update_status.assert_awaited_once_with(task_new, Status.QUEUED)



async def test_start_processing_task_not_found(service, repo):
    repo.get_with_result.return_value = None

    with patch.object(service, "_enqueue") as enqueue:
        with pytest.raises(TaskNotFoundError):
            await service.start_processing(task_id=1)

    enqueue.assert_not_called()
    repo.update_status.assert_not_awaited()



async def test_start_processing_invalid_status(service, repo, task_new):
    task_new.status = Status.DONE
    repo.get_with_result.return_value = task_new

    with patch.object(service, "_enqueue") as enqueue:
        with pytest.raises(TaskCannotBeProcessedError):
            await service.start_processing(task_id=1)

    enqueue.assert_not_called()
    repo.update_status.assert_not_awaited()


async def test_start_processing_rolls_back_on_enqueue_failure(service, repo, task_new):
    repo.get_with_result.return_value = task_new
    repo.update_status.return_value = task_new

    with patch.object(service, "_enqueue", side_effect=RuntimeError("broker down")):
        with pytest.raises(RuntimeError, match="broker down"):
            await service.start_processing(task_id=1)

    assert repo.update_status.await_args_list == [
        ((task_new, Status.QUEUED), {}),
        ((task_new, Status.NEW), {}),
    ]