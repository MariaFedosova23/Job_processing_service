import asyncio
import logging

from src.database.repositories.task import TaskRepository
from src.database.database import get_session
from src.constants import INTERVAL

logger = logging.getLogger('job_processing_service')


class LeaseLostError(Exception):
    """Владение задачей потеряно — результат сохранять нельзя."""
    pass


async def watch_lease(
    task_id: int,
    owner_token: str,
    *,
    initial_deadline: float,
    lease_seconds: int,
) -> None:
    loop = asyncio.get_running_loop()
    deadline = initial_deadline

    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise LeaseLostError("Истёк срок владения")

        await asyncio.sleep(min(INTERVAL, remaining))

        remaining = deadline - loop.time()
        if remaining <= 0:
            raise LeaseLostError("Истёк срок владения")

        renewal_started = loop.time()
        logger.info('renewal_started=%s', renewal_started)

        try:
            async with asyncio.timeout(min(5.0, remaining)):
                async with get_session() as session:
                    repo = TaskRepository(session)
                    renewed = await repo.renew_lease(
                        task_id,
                        owner_token=owner_token,
                        lease_seconds=lease_seconds,
                    )
            if renewed is None:
                raise LeaseLostError("Владение потеряно")
        except LeaseLostError as err:
            raise
        except Exception as exc:
            raise LeaseLostError(
                "Не удалось подтвердить владение"
            ) from exc


        deadline = renewal_started + lease_seconds


async def run_with_lease(work, guard):
    """
    Оркестратор: запускает воркер и сторожа.
    """
    work_task = asyncio.create_task(work)
    guard_task = asyncio.create_task(guard)
    try:
        await asyncio.wait(
            {work_task, guard_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        
        if guard_task.done():

            await guard_task

        return await work_task

    finally:

        work_task.cancel()
        guard_task.cancel()

        await asyncio.gather(
            work_task,
            guard_task,
            return_exceptions=True
        )

   
    