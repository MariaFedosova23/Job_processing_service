TASK_PRIORITY_LOW = 1
TASK_PRIORITY_DEFAULT = 3
TASK_PRIORITY_HIGH = 5

TASK_TITLE_MIN_LENGTH = 3
TASK_TITLE_MAX_LENGTH = 200
TASK_TEXT_MIN_LENGTH = 1

TASK_EXTERNAL_ID_MAX_LENGTH = 100

MAX_LENGTH_OWNER_TOKEN = 50

MAX_LENGTH_RUN_ID = 50

DEFAULT_LIMIT = 10
MIN_LIMIT = 1
MAX_LIMIT = 100

DEFAULT_OFFSET = 0
MIN_OFFSET = 0

SIZE_LOGGING_FILES = 5 * 1024 * 1024
COUNT_LOGGING_FILES = 5

TIME_CELERY_TASK = 10


RETRY_BACKOFF_MAX=60

MAX_TRIES=3

FORBIDDEN_WORD_IN_TEXT = ('мат', 'спам')

SOCKET_TIMEOUT = 2

LEASE_SECONDS = 300

INTERVAL = LEASE_SECONDS / 3

SOFT_TIME = LEASE_SECONDS * 2

TIME_LIMIT = LEASE_SECONDS * 3

MAX_FILE_SIZE = 1024 * 1024 * 10

ALLOWED_TYPES = {
    'application/pdf', 'text/plain', 'image/png',
    'image/jpeg',
}


ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    'new': {'queued', 'cancelled'},
    'queued': {'processing', 'new', 'cancelled'},
    'processing': {'done', 'error', 'queued', 'cancelled'},
    'done': set(),
    'error': {'queued', 'cancelled', 'new'},     
    'cancelled': set(),
}

API_PATCH_TRANSITIONS: dict[str, set[str]] = {
    'done': {'new'},
    'error': {'new'},
    'cancelled': {'new'},
}

WORKER_TRANSITIONS: dict[str, set[str]] = {
    'queued':     {'processing'},
    'processing': {'done', 'error', 'queued'},
}
