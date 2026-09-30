import os
import logging
import redis.asyncio as aioredis 


from src.database.repositories.health import HealthRepository
from src.constants import SOCKET_TIMEOUT

logger = logging.getLogger('job_processing_service')


class HealthService:
    def __init__(
        self,
        repo: HealthRepository,
        redis_url: str | None = None
    ):
        self.repo = repo
        self.redis_url = redis_url or os.getenv('REDIS_URL')

    async def check_postgres(self) -> dict[str, any]:
        """Проверяет соединение с PostgreSQL через лёгкий запрос SELECT 1."""
        if await self.repo.check_connection():
            return {'status': 'ok'}
        return {'status': 'error', 'detail': 'Cannot connect to PostgreSQL'}

    async def check_redis(self) -> dict[str, any]:
        """Проверяет Redis через PING."""
        if not self.redis_url:
            return {'status': 'error', 'detail': 'REDIS_URL is not set'}
        client = aioredis.from_url(
            self.redis_url,
            socket_timeout=SOCKET_TIMEOUT,
            socket_connect_timeout=SOCKET_TIMEOUT,
    )
        try:
            
            if client.ping():
                return {'status': 'ok'}
            
            return {'status': 'error', 'detail': 'PING returned False'}
        except Exception as e:
            logger.error(f"Redis check failed: {e}")
            return {"status": "error", "detail": str(e)}
        finally:
            await client.aclose()

    async def readiness_check(
            self
    ) -> dict[str, any]:
        """
        Выполняет все проверки и возвращает общий статус.
        Если хоть одна зависимость упала — общий статус 'not_ready'.
        """
        checks = {}

        # 1. Postgres
        postgres_res = await self.check_postgres()
        checks['postgres'] = postgres_res

        # 2. Redis
        redis_res = await self.check_redis()
        checks['redis'] = redis_res


        all_ok = all(c["status"] == 'ok' for c in checks.values())
        status = 'ready' if all_ok else 'not_ready'

        return {
            'tatus': status,
            'dependencies': checks,
        }
