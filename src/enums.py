from enum import StrEnum


class Status(StrEnum):
    NEW = 'new'
    QUEUED = 'queued'
    PROCESSING = 'processing'
    DONE = 'done'
    ERROR = 'error'
    CANCELLED = 'cancelled'
    CANCELLING = 'cancelling'


class Caller(StrEnum):
    API_USER = 'api_user'
    WORKER = 'worker'


class OutboxStatus(StrEnum):
    PENDING = 'pending'
    SENT = 'sent'
    FAILED = 'failed'


class TaskOutcome(StrEnum):
    """Ожидаемый исход выполнения Celery-задачи."""

    DONE = 'done'
    CANCELLED = 'cancelled'
    SKIPPED = 'skipped'
    REJECTED = 'rejected'
    