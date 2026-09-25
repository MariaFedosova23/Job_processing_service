

class DomainError(Exception):
    """Базовое доменное исключение — общий родитель для всех наших ошибок."""


class TaskNotFoundError(DomainError):
    def __init__(self, task_id: int) -> None:
        self.task_id = task_id
        super().__init__(f"Задание {task_id} не найдено")


class DuplicateExternalIdError(DomainError):
    def __init__(self, external_id: str) -> None:
        self.external_id = external_id
        super().__init__(f"external_id={external_id} уже существует")


class InvalidStatusTransitionError(DomainError):
    def __init__(self, task_id: int, old_status: str, new_status: str) -> None:
        self.task_id = task_id
        self.old_status = old_status
        self.new_status = new_status
        super().__init__(
            f"Недопустимый переход статуса задачи {task_id}: {old_status} -> {new_status}"
        )


class TaskCannotBeProcessedError(DomainError):
    def __init__(self, task_id: int, status: str) -> None:
        self.status = status
        super().__init__(f"Задание задачи {task_id} в статусе '{status}' нельзя обработать")


class TaskProcessingError(Exception):
    """
    Базовая бизнес-ошибка обработки задачи.
    """
    user_message: str = 'Ошибка обработки задачи'
    def __init__(self, message: str | None = None):
        if message is not None:
            self.user_message = message
        super().__init__(self.user_message)


class ForbiddenWordsError(TaskProcessingError):
    """В тексте задачи найдены запрещённые слова."""
    def __init__(self, found_words: list[str]):
        self.found_words = found_words
        words = ', '.join(found_words)
        super().__init__(f'Найдены запрещённые слова: {words}')
