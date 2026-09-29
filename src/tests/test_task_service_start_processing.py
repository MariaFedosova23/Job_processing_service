from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import pytest
from unittest.mock import patch
import redis
from src.database.repositories.task import TaskRepository
from src.services.task_service import TaskService, StartProcessingResult
from src.enums import Status
from src.services.exceptions import (
    TaskNotFoundError, TaskCannotBeProcessedError, TaskCannotBeRetryError
)
# from src.worker.tasks.tasks import process_task
from src.services.task_service import TaskService
from src.database.models.task import TaskDB, TaskResultDB
# from src.api.v1.dependencies import get_task_service
from src.main import app

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


async def test_start_processing_happy_path(
    service, repo, task_new, enqueue_mock
):
    repo.get_with_result.return_value = task_new
    repo.update_status.return_value = task_new

    result = await service.start_processing(task_id=1)

    enqueue_mock.assert_called_once_with(1)
    repo.update_status.assert_awaited_once_with(
        task_new, Status.QUEUED
    )
    assert result.task is task_new
    assert result.celery_task_id == "celery-abc"


async def test_start_processing_task_not_found(service, repo, enqueue_mock):
    repo.get_with_result.return_value = None

    with pytest.raises(TaskNotFoundError):
        await service.start_processing(task_id=1)

    enqueue_mock.assert_not_called()
    repo.update_status.assert_not_awaited()


async def test_start_processing_invalid_status(
    service: TaskService,
    repo: AsyncMock,
    task_new: MagicMock,
    enqueue_mock
):
    task_new.status = Status.DONE
    repo.get_with_result.return_value = task_new
    with pytest.raises(TaskCannotBeProcessedError):
        await service.start_processing(task_id=1)

    enqueue_mock.assert_not_called()
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


@pytest.mark.integration
async def test_update_status_persists_to_db(db_session):
    task = TaskDB(
        title="t", text="x", priority=1,
        external_id="1c-1", status=Status.NEW,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    repo = TaskRepository(db_session)
    updated = await repo.update_status(task, Status.QUEUED)

    assert updated.status == Status.QUEUED

    await db_session.refresh(task)
    assert task.status == Status.QUEUED
    assert task.status == Status.QUEUED.value


@pytest.mark.integration
async def test_second_process_returns_409(
        client, task_factory
):
    task = await task_factory(status=Status.NEW)
  
    first = await client.post(f"/api/v1/tasks/{task.id}/process")
    assert first.status_code == 200, first.text

    second = await client.post(f"/api/v1/tasks/{task.id}/process")
    assert second.status_code == 409, second.text



@pytest.mark.integration
async def test_success_processing(
        client,
        celery_worker,
        task_factory
    ):
    task = await task_factory(status=Status.NEW)
    task_id = task.id

    result = await client.post(f"/api/v1/tasks/{task.id}/process")
    assert result.status_code == 200, result.text

    from sqlalchemy import select
    from src.database.database import engine_worker

    deadline = asyncio.get_event_loop().time() + 30
    final_statuses = {Status.DONE, Status.ERROR}
    status = error = None
    while asyncio.get_event_loop().time() < deadline:
        async with engine_worker.connect() as conn:
            row = (await conn.execute(
                select(TaskDB.status, TaskDB.error).where(TaskDB.id == task_id)
            )).one_or_none()
        if row and row.status in final_statuses:
            status, error = row.status, row.error
            break
        await asyncio.sleep(0.1)

    assert status == Status.DONE, f"status={status}, error={error}"
    assert error is None

    async with engine_worker.connect() as conn:
        result_row = (await conn.execute(
            select(TaskResultDB.word_count, TaskResultDB.original_length)
            .where(TaskResultDB.task_id == task_id)
        )).one_or_none()

    assert result_row is not None
    assert result_row.word_count == 1        # "Описание"
    assert result_row.original_length == len("Описание")


@pytest.mark.integration
async def test_process_error(
    client,
    celery_worker,
    task_factory
):
    task = await task_factory(status=Status.NEW, text='мат спам')
    task_id = task.id

    result = await client.post(f"/api/v1/tasks/{task.id}/process")
    assert result.status_code == 200, result.text

    from sqlalchemy import select
    from src.database.database import engine_worker

    deadline = asyncio.get_event_loop().time() + 30
    final_statuses = {Status.DONE, Status.ERROR}
    status = error = None
    while asyncio.get_event_loop().time() < deadline:
        async with engine_worker.connect() as conn:
            row = (await conn.execute(
                select(TaskDB.status, TaskDB.error).where(TaskDB.id == task_id)
            )).one_or_none()
        if row and row.status in final_statuses:
            status, error = row.status, row.error
            break
        await asyncio.sleep(0.1)

    assert status == Status.ERROR, f"status={status}, error={error}"
    assert error is not None


@pytest.mark.integration
async def test_process_retry(
    client,
    celery_worker,
    task_factory
):
    task = await task_factory(
        status=Status.ERROR, text='without forbidden words'
    )
    task_id = task.id

    result = await client.post(f"/api/v1/tasks/{task.id}/retry")
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["id"] == task_id
    assert body["status"] == Status.QUEUED.value
    assert body["celery_task_id"] is not None
    from sqlalchemy import select
    from src.database.database import engine_worker

    deadline = asyncio.get_event_loop().time() + 30
    final_statuses = {Status.DONE, Status.ERROR}
    status = error = None
    while asyncio.get_event_loop().time() < deadline:
        async with engine_worker.connect() as conn:
            row = (await conn.execute(
                select(TaskDB.status, TaskDB.error).where(TaskDB.id == task_id)
            )).one_or_none()
        if row and row.status in final_statuses:
            status, error = row.status, row.error
            break
        await asyncio.sleep(0.1)

    assert status == Status.DONE, f"status={status}, error={error}"
    assert error is None


async def test_retry_success_task(

    service: TaskService,
    repo: AsyncMock,
    task_new: MagicMock,
    enqueue_mock
):
    task_new.status = Status.DONE
    repo.get_with_result.return_value = task_new
    with pytest.raises(TaskCannotBeRetryError):
        await service.retry_task(task_id=1)

    enqueue_mock.assert_not_called()
    repo.update_status.assert_not_awaited()
  
