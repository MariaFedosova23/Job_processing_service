from enum import StrEnum


class Status(StrEnum):
    NEW = 'new'
    QUEUED = 'queued'
    PROCESSING = 'processing'
    DONE = 'done'
    ERROR = 'error'
    CANCELLED = 'cancelled'


class Caller(StrEnum):
    API_USER = 'api_user'
    WORKER = 'worker'