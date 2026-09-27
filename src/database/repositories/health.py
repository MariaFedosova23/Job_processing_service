from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger('job_processing_service')

class HealthRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_connection(self) -> bool:
        """Выполняет SELECT 1 и возвращает True, если всё ок."""
        try:
            logger.info('Starting DB health check (SELECT 1)...')
            result = await self.session.execute(select(1))
            val = result.scalar()
            logger.info(f'DB health check succeeded. Got value: {val}')
            return True
        except Exception as e:
            logger.error(
                f'Unexpected error during DB check: {type(e).__name__}: '
                f'{e}'
            )
            return False
