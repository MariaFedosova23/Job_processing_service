
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, or_

from src.database.models.outbox_tasks import OutboxTaskDB
from src.enums import OutboxStatus

class OutboxRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def lock_pending_batch(self, limit: int) -> list[OutboxTaskDB]:
        'Забирает Pending-записи и блокирует их до конца транзакции.'
        stmt = (
            select(OutboxTaskDB)
            .where(OutboxTaskDB.status == OutboxStatus.PENDING)
            .where(
                or_(
                    OutboxTaskDB.next_retry_at.is_(None),
                    OutboxTaskDB.next_retry_at <= func.now(),
                )
            )
        .order_by(OutboxTaskDB.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    