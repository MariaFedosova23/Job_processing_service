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

TIME_CELERY_TASK = 7

TIME_CELERY_BEAT_IN_MINUTE = 2


RETRY_BACKOFF_MAX=60

MAX_TRIES=3

FORBIDDEN_WORD_IN_TEXT = ('мат', 'спам')

SOCKET_TIMEOUT = 2

LEASE_SECONDS = 300

INTERVAL = LEASE_SECONDS / 6

SOFT_TIME = LEASE_SECONDS * 2

TIME_LIMIT = LEASE_SECONDS * 3

MAX_FILE_SIZE = 1024 * 1024 * 10

ALLOWED_TYPES = {
    'application/pdf', 'text/plain', 'image/png',
    'image/jpeg', 'image/jpg',
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

# database/models/outbox_tasks
MAX_TASK_NAME = 50
MAX_IDEMPOTENCY_KEY = 255


CELERY_TASK_PROCESS_NAME = 'worker.process_task'

CELERY_TASK_GET_FILE_NAME = 'worker.get_file'

OUTBOX_BATCH_SIZE = 20
OUTBOX_MAX_ATTEMPTS = 10
OUTBOX_BACKOFF_CAP_SECONDS = 15

OUTBOX_RELAY_INTERVAL_SECONDS = 5.0


# users

MAX_LENGTH_USERNAME = 20
MIN_LENGTH_USERNAME = 5

MAX_LENGTH_PASSWORD = 128
MIN_LENGTH_PASSWORD = 8

MAX_LENGTH_PASSWORD_HASH = 255


DEFAULT_LIMIT_USERS = 10
MAX_LIMIT_USERS = 100
MIN_LIMIT_USERS = 1

#  JWT

JWT_ACCESS_TOKEN_EXPIRES_IN_MINUTES = 30


