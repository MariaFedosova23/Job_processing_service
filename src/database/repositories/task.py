from datetime import datetime, timedelta

from sqlalchemy import select, update, and_, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

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


    async def update_status(
        self,
        task_id: int,
        *,
        expected_status: Status,
        new_status: Status,  
    ) -> TaskDB | None:
        """Обновление статуса."""
        values: dict = {'status': new_status}
        if new_status == Status.NEW:
            values.update({
                'run_id': None,
                'owner_token': None,
                'lease_until': None,
                'started_at': None,
                'error': None,
            })
        elif new_status == Status.CANCELLED:
            values.update({
                'owner_token': None,
                'lease_until': None,
                'finished_at': func.now()
            })

        stmt = (
            update(TaskDB)
            .where(TaskDB.id == task_id)
            .where(TaskDB.status == expected_status) 
            .values(**values)
            .returning(TaskDB)
        )
        result = await self.session.execute(stmt)
        task = result.scalar_one_or_none()
        await self.session.commit()
        return task
            

    async def mark_processing(
        self,
        task_id: int,
        run_id: str,
        *,
        owner_token: str,
        lease_seconds: int,
        allow_processing: bool = False,
    ) -> TaskDB | None:
  

        condition = or_(
            TaskDB.status == Status.QUEUED,
            and_(
                TaskDB.status == Status.PROCESSING,
                allow_processing,
                TaskDB.lease_until < func.now(),
            ),
        )

        stmt = (
            update(TaskDB)
            .where(TaskDB.id == task_id)
            .where(condition)
            .where(TaskDB.run_id == run_id)
            .values(
                status=Status.PROCESSING,
                started_at=func.now(),
                owner_token=owner_token,
                lease_until=func.now() + timedelta(seconds=lease_seconds),
                error=None,
            )
            .returning(TaskDB)
        )
        result = await self.session.execute(stmt)
        task = result.scalar_one_or_none()
        await self.session.commit()
        return task

    async def release_to_queued(
            self,
            task_id: int,
            owner_token: str,
    ) -> TaskDB | None:
        """
        PROCESSING → QUEUED, освобождает владение.
        """
        stmt = (
            update(TaskDB)
            .where(TaskDB.id == task_id)
            .where(TaskDB.owner_token == owner_token)
            .where(TaskDB.status == Status.PROCESSING)
            .values(
                status=Status.QUEUED,
                owner_token=None,
                lease_until=None,
                started_at=None,
                error=None,
            )
            .returning(TaskDB)
        )
        result = await self.session.execute(stmt)
        task = result.scalar_one_or_none()
        await self.session.commit()
        return task

    
    async def mark_queued_new_task(
            self,
            task_id: int,
            run_id: str
    ) -> TaskDB | None:
        stmt = (
            update(TaskDB)
                .where(TaskDB.id == task_id)
                .where(TaskDB.status == Status.NEW)
                .values(
                    status=Status.QUEUED,
                    error=None,
                    run_id=run_id
                )
                .returning(TaskDB)
        )
        result = await self.session.execute(stmt)
        task = result.scalar_one_or_none()
        await self.session.commit()
        return task

    async def mark_queued_error_task(self, task_id: int, run_id: str) -> TaskDB | None:
        stmt = (
            update(TaskDB)
                .where(TaskDB.id == task_id)
                .where(TaskDB.status == Status.ERROR)
                .values(
                    status=Status.QUEUED,
                    error=None,
                    run_id=run_id,
                )
                .returning(TaskDB)
        )
        result = await self.session.execute(stmt)
        task = result.scalar_one_or_none()
        await self.session.commit()
        return task
        
    async def revert_to_new_status(
        self,
        task_id: int,
        run_id: str
    ) -> TaskDB | None:
        """QUEUED -> NEW."""
        stmt = (
            update(TaskDB)
            .where(TaskDB.id == task_id)
            .where(TaskDB.status == Status.QUEUED)
            .where(TaskDB.run_id == run_id)
            .values(
                status=Status.NEW,
                run_id=None,
                error=None,
            )
            .returning(TaskDB)
        )
        result = await self.session.execute(stmt)
        task = result.scalar_one_or_none()
        await self.session.commit()
        return task

    async def mark_failed(
        self,
        task_id: int,
        *,
        error: str,
        owner_token: str,
    ) -> TaskDB | None:
        """
        Ставит задаче статус ERROR,
        записывает текст ошибки и время завершения.
        Возвращает None, если задачи нет.
        """
        stmt = (
            update(TaskDB)
            .where(TaskDB.id == task_id)
            .where(TaskDB.owner_token == owner_token)   
            .where(TaskDB.status == Status.PROCESSING)
            .values(
                status=Status.ERROR,
                error=error,
                finished_at=func.now(),
                owner_token=None,
                lease_until=None,
            )
            .returning(TaskDB)
        )
        task = (await self.session.execute(stmt)).scalar_one_or_none()
        await self.session.commit()
        return task


    async def save_result_and_complete(
        self,
        task_id: int,
        *,
        owner_token: str,
        original_length: int,
        word_count: int,
        run_id: str,
    ) -> TaskDB | None:
        result_stmt = (
            update(TaskDB)
            .where(TaskDB.id == task_id)
            .where(TaskDB.owner_token == owner_token) 
            .where(TaskDB.status == Status.PROCESSING)
            .where(TaskDB.run_id == run_id)
            .where(TaskDB.lease_until > func.now())
            .values(
                status=Status.DONE,
                finished_at=func.now(),
                error=None,
                owner_token=None,   
                lease_until=None,
            )
            .returning(TaskDB)
        )
        task = (
            await self.session.execute(result_stmt)
        ).scalar_one_or_none()
        
        if task is None:
            await self.session.rollback()
            return None

        stmt = (
            insert(TaskResultDB)
            .values(
                task_id=task_id,
                original_length=original_length,
                word_count=word_count,
                processed_at=func.now(),
            )
            .on_conflict_do_nothing(index_elements=['task_id'])
        )
        await self.session.execute(stmt)

        await self.session.commit()
        return task

    async def renew_lease(
        self,
        task_id: int,
        *,
        owner_token: str,
        lease_seconds: int
    ) -> datetime | None:
        """
        Продлевает lease задачи, если владение всё ещё есть
        и lease не истёк.

        Возвращает True, если продление удалось,
        False — если владение потеряно / lease истёк.
        """
     
        stmt = (
            update(TaskDB)
            .where(TaskDB.id == task_id)
            .where(TaskDB.owner_token == owner_token)
            .where(TaskDB.status == Status.PROCESSING)
            .where(TaskDB.lease_until > func.now())
            .values(
                lease_until=func.now() + timedelta(seconds=lease_seconds)
            )
            .returning(TaskDB.lease_until)

        )
        result =  await self.session.execute(stmt)
        new_lease_until = result.scalar_one_or_none()
        await self.session.commit()
        return new_lease_until

    async def confirm_cancellation(
        self,
        task_id: int,
        *,
        owner_token: str,
    ) -> TaskDB | None:
        """Подтверждает отмену: CANCELLING → CANCELLED."""
        stmt = (
            update(TaskDB)
            .where(TaskDB.id == task_id)
            .where(TaskDB.status == Status.CANCELLING)
            .where(TaskDB.owner_token == owner_token)
            .values(
                status=Status.CANCELLED,
                owner_token=None,
                lease_until=None,
                finished_at=func.now(),
            )
            .returning(TaskDB)
    )
        result = await self.session.execute(stmt)
        task = result.scalar_one_or_none()
        await self.session.commit()
        return task

    async def sweep_stale_cancellations(self) -> list[TaskDB]:
        stmt = (
            update(TaskDB)
            .where(TaskDB.status == Status.CANCELLING)
            .where(TaskDB.lease_until < func.now())
            .values(
                status=Status.CANCELLED,
                owner_token=None,
                lease_until=None,
                finished_at=func.now(),
            )
            .returning(TaskDB.id)
        )
        result = await self.session.execute(stmt)
        tasks_ids = list(result.scalars().all())
        await self.session.commit()
        return tasks_ids

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

        
