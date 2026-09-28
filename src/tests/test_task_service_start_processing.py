from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis
from src.services.task_service import TaskService, StartProcessingResult
from src.enums import Status
from src.services.exceptions import TaskNotFoundError, TaskCannotBeProcessedError
# from src.worker.tasks.tasks import process_task
from src.services.task_service import TaskService


@pytest.fixture
def repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def task_new():
    task = MagicMock()
    task.id = 1
    task.status = Status.NEW
    return task


@pytest.fixture
def enqueue_mock():
    return MagicMock(return_value="celery-abc")

@pytest.fixture
def service(repo, enqueue_mock):
    return TaskService(repo, enqueue=enqueue_mock)

async def test_start_processing_happy_path(service, repo, task_new, enqueue_mock):
    repo.get_with_result.return_value = task_new
    repo.update_status.return_value = task_new

    result = await service.start_processing(task_id=1)

    enqueue_mock.assert_called_once_with(1)
    assert result.celery_task_id == "celery-abc"



async def test_start_processing_task_not_found(service, repo, enqueue_mock):
    repo.get_with_result.return_value = None

    with pytest.raises(TaskNotFoundError):
        await service.start_processing(task_id=1)

    enqueue_mock.assert_not_called()
    repo.update_status.assert_not_awaited()



async def test_start_processing_invalid_status(service: TaskService, repo: AsyncMock, task_new: MagicMock):
    task_new.status = Status.DONE
    repo.get_with_result.return_value = task_new

    with patch.object(service, "_enqueue") as enqueue:
        with pytest.raises(TaskCannotBeProcessedError):
            await service.start_processing(task_id=1)

    enqueue.assert_not_called()
    repo.update_status.assert_not_awaited()


async def test_start_processing_rolls_back_on_enqueue_failure(
    service, repo, task_new, enqueue_mock
):
    repo.get_with_result.return_value = task_new
    repo.update_status.return_value = task_new

    enqueue_mock.side_effect = RuntimeError("broker down")

    with pytest.raises(RuntimeError, match="broker down"):
        await service.start_processing(task_id=1)

    enqueue_mock.assert_called_once_with(1)
    assert repo.update_status.await_args_list == [
        ((task_new, Status.QUEUED), {}),
        ((task_new, Status.NEW), {}),
    ]



async def test_enqueue_calls_celery_delay():
    mock_result = MagicMock(id="celery-xyz")
    mock_delay = MagicMock(return_value=mock_result)

    def enqueue(task_id: int) -> str:
        return mock_delay(task_id).id

    service = TaskService(repo=AsyncMock(), enqueue=enqueue)
    celery_id = service._enqueue(task_id=999)

    mock_delay.assert_called_once_with(999)
    assert celery_id == "celery-xyz"