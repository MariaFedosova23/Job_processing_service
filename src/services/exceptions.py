

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
    def __init__(self, old_status: str, new_status: str) -> None:
        self.old_status = old_status
        self.new_status = new_status
        super().__init__(
            f"Недопустимый переход статуса: {old_status} -> {new_status}"
        )


class TaskCannotBeProcessedError(DomainError):
    def __init__(self, status: str) -> None:
        self.status = status
        super().__init__(f"Задание в статусе '{status}' нельзя обработать")