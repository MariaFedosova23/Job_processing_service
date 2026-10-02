import asyncio
import threading
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from src.database.models.task import TaskDB
from src.enums import Status
from src.constants import INTERVAL

logger = logging.getLogger('job_processing_service')

class LeaseHeartbeat:
    """
    Продлевает lease задачи в отдельном потоке.
    Не блокируется основной бизнес-логикой.
    """

    def __init__(
        self,
        session_factory,          
        task_id: int,
        owner_token: str,
        lease_seconds: int,
    ):
        self.session_factory = session_factory
        self.task_id = task_id
        self.owner_token = owner_token
        self.lease_seconds = lease_seconds
        self.interval = INTERVAL

        self._stop = threading.Event()
        self._lost = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_lost(self) -> bool:
        return self._lost.is_set()

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run,
            name=f"heartbeat-task-{self.task_id}",
            daemon=True,
        )
        self._thread.start()
        logger.debug("Heartbeat запущен: task_id=%s", self.task_id)

    def _run(self) -> None:
        try:
            while not self._stop.wait(self.interval):
                asyncio.run(self.renew_once())
                if self._lost.is_set():
                    return 
        except Exception:
            logger.exception(
                "Heartbeat упал: task_id=%s", self.task_id
            )
            self._lost.set()

    async def renew_once(self) -> None:
        try:
            async with self.session_factory() as session:
                now = datetime.now(timezone.utc)
                stmt = (
                    update(TaskDB)
                    .where(TaskDB.id == self.task_id)
                    .where(TaskDB.owner_token == self.owner_token)
                    .where(TaskDB.status == Status.PROCESSING)
                    .values(
                        lease_until=now + timedelta(seconds=self.lease_seconds)
                    )
                    .returning(TaskDB.id)
        
                )
                result =  await session.execute(stmt)
                task_id = result.scalar_one_or_none()
                await session.commit()

                if task_id is None:
                    logger.warning(
                        "Lease потерян: task_id=%s, owner=%s",
                        self.task_id, self.owner_token,
                        extra={"event": "lease_lost", "task_id": self.task_id},
                    )
                    self._lost.set()
                else:
                    logger.debug(
                        "Lease продлён: task_id=%s, until=%s",
                        self.task_id,
                        now + timedelta(seconds=self.lease_seconds),

                    )
        except Exception:
            logger.exception(
                "renew_lease упал: task_id=%s", self.task_id
            )
            self._lost.set()   

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval + 5)
        logger.debug("Heartbeat остановлен: task_id=%s", self.task_id) 
