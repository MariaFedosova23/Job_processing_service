from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.task import TaskDB, TaskResultDB
from src.database.models.file import FileDB
from src.enums import Status


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_with_result(self, task_id: int) -> TaskDB | None:
        stmt = (
            select(TaskDB).where(TaskDB.id == task_id).options(
                selectinload(TaskDB.result)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
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

    async def mark_processing(
        self,
        task_id: int,
        *,
        owner_token: str,
        lease_seconds: int,
        started_at: datetime,
        allow_processing: bool = False,
    ) -> TaskDB | None:
        started_at = started_at
        lease_until = started_at + timedelta(seconds=lease_seconds)
        allowed = (
            Status.QUEUED, Status.PROCESSING
        ) if allow_processing else (Status.QUEUED,)


        stmt = (
            update(TaskDB)
            .where(TaskDB.id == task_id)
            .where(TaskDB.status.in_(allowed))
            .values(
                status=Status.PROCESSING,
                started_at=started_at,
                error=None,
            )
            .returning(TaskDB)
        )
        result = await self.session.execute(stmt)
        task = result.scalar_one_or_none()
        await self.session.commit()
        
        return task
    
    async def mark_queued_new_task(self, task_id: int) -> TaskDB | None:
        stmt = (
            update(TaskDB)
                .where(TaskDB.id == task_id)
                .where(TaskDB.status == Status.NEW)
                .values(
                    status=Status.QUEUED,
                    error=None,
                )
                .returning(TaskDB)
        )
        result = await self.session.execute(stmt)
        task = result.scalar_one_or_none()
        await self.session.commit()
        return task

    async def mark_queued_error_task(self, task_id: int) -> TaskDB | None:
        stmt = (
            update(TaskDB)
                .where(TaskDB.id == task_id)
                .where(TaskDB.status == Status.ERROR)
                .values(
                    status=Status.QUEUED,
                    error=None,
                )
                .returning(TaskDB)
        )
        result = await self.session.execute(stmt)
        task = result.scalar_one_or_none()
        await self.session.commit()
        return task
        


    async def save_result(
        self,
        task_id: int,
        *,
        original_length: int,
        word_count: int,
        processed_at: datetime,
    ) -> TaskResultDB | None:
        task = await self.session.get(TaskDB, task_id)
        if task is None:
            return None
        if task.status == Status.Cancelled:
            return
        
        result = TaskResultDB(
            task_id=task_id,
            original_length=original_length,
            word_count=word_count,
            processed_at=processed_at,
        )
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return result


    async def mark_done(
        self,
        task_id: int,
        *,
        finished_at: datetime
    ) -> TaskDB | None:
        
        task = await self.session.get(TaskDB, task_id)
        if task is None:
            return None
        task.status = Status.DONE
        task.finished_at = finished_at
        task.error = None
        await self.session.commit()
        # await self.session.refresh(task)
        return task

    async def mark_failed(
        self,
        task_id: int,
        *,
        error: str,
        finished_at: datetime,
    ) -> TaskDB | None:
        """
        Ставит задаче статус ERROR,
        записывает текст ошибки и время завершения.
        Возвращает None, если задачи нет.
        """
        task = await self.session.get(TaskDB, task_id)
        if task is None:
            return None

        task.status = Status.ERROR       
        task.error = error
        task.finished_at = finished_at
        await self.session.commit()
        # await self.session.refresh(task)
        return task


    async def save_result_and_complete(
        self,
        task_id: int,
        *,
        original_length: int,
        word_count: int,
        processed_at: datetime,
        finished_at: datetime,
    ) -> TaskDB | None:
        task = await self.session.get(TaskDB, task_id)
        if task is None:
            return None
        if task.status == Status.CANCELLED:
            return

        existing = await self.session.execute(
            select(TaskResultDB).where(TaskResultDB.task_id == task_id)
        )
        if existing.scalar_one_or_none() is None:
            self.session.add(TaskResultDB(
                task_id=task_id,
                original_length=original_length,
                word_count=word_count,
                processed_at=processed_at,
            ))

        task.status = Status.DONE
        task.finished_at = finished_at
        task.error = None

        await self.session.commit()
        # await self.session.refresh(task)
        return task

    async def create_file(
        self,
        task_id: int | None,
        original_name: str,
        internal_name: str,
        mime_type: str,
        size_bytes: int,
    ) -> FileDB:
        file_obj = FileDB(
            task_id=task_id,
            original_name=original_name,
            internal_name=internal_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
        )
        self.session.add(file_obj)
        await self.session.commit()
        await self.session.refresh(file_obj)
        return file_obj

        
