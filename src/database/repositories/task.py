from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.task import TaskDB
from src.schemas.tasks import Status


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, task_id: int) -> TaskDB | None:
        return await self.session.get(TaskDB, task_id)

    async def add(self, task: TaskDB) -> TaskDB:
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def delete(self, task: TaskDB) -> None:
        await self.session.delete(task)
        await self.session.commit()

    async def get_by_external_id(self, external_id: str) -> TaskDB | None:
        stmt = select(TaskDB).where(TaskDB.external_id == external_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_filtered(
        self,
        *,
        status: Status | None = None,
        priority: int | None = None,
        limit: int,
        offset: int,
    ) -> list[TaskDB]:
        stmt = select(TaskDB)
        if status is not None:
            stmt = stmt.where(TaskDB.status == status)
        if priority is not None:
            stmt = stmt.where(TaskDB.priority == priority)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, task: TaskDB, new_status: Status) -> TaskDB:
        task.status = new_status
        await self.session.commit()
        await self.session.refresh(task)
        return task
