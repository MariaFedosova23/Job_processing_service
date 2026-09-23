from celery import Task
from database.database import AsyncSessionLocal

class DatabaseTask(Task):
    """
    Кастомный базовый класс задачи Celery.
    Автоматически создаёт и закрывает сессию SQLAlchemy для каждой задачи.
    """
    _session = None

    @property
    def session(self):
        """Ленивая инициализция сессии."""
        if self._session is None:
            self._session = AsyncSessionLocal()
        return self._session

    def after_return(self, *args, **kwargs):
        """Вызывается Celery после завершения задачи (успех или ошибка)."""
        if self._session is not None:
            self._session.close()
            self._session = None
        super().after_return(*args, **kwargs)