import logging
import os
import sys
import asyncio
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

from src.database import Base, get_db
from src.main import app
from src.enums import Status
from src.database.models.task import TaskDB
from src.database.repositories.task import TaskRepository
from src.api.v1.dependencies import get_task_service
from src.services.task_service import TaskService

DATABASE_URL = os.getenv('TEST_DATABASE_URL')
if not DATABASE_URL:
    raise ValueError('DATABASE_URL не установлена в .env')

logger = logging.getLogger('job_processing_service')

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest_asyncio.fixture(scope='session')
async def engine():
    engine = create_async_engine(DATABASE_URL, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.error(
            'Не удалось подключиться к тестовой БД: %s', type(e).__name__
        )
        raise

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncSession:
    SessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with SessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def client(db_session) -> AsyncClient:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def task_factory(db_session: AsyncSession):
    created_tasks = []

    async def create_task(
        *,
        title: str = "Тестовая задача",
        text: str = "Описание",
        priority: int = 1,
        external_id: str | None = None,
        status: Status = Status.NEW,
    ) -> TaskDB:
        task = TaskDB(
            title=title,
            text=text,
            priority=priority,
            external_id=external_id or f"test-{len(created_tasks) + 1}",
            status=status,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)
        created_tasks.append(task)
        return task

    yield create_task

@pytest_asyncio.fixture
async def override_task_service(db_session):
    def fake_enqueue(task_id: int) -> str:
        return "celery-abc"

    def override():
        return TaskService(TaskRepository(db_session), enqueue=fake_enqueue)

    app.dependency_overrides[get_task_service] = override
    yield
    app.dependency_overrides.pop(get_task_service, None)