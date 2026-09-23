TASK_PRIORITY_LOW = 1
TASK_PRIORITY_DEFAULT = 3
TASK_PRIORITY_HIGH = 5

TASK_TITLE_MIN_LENGTH = 3
TASK_TITLE_MAX_LENGTH = 200
TASK_TEXT_MIN_LENGTH = 1

TASK_EXTERNAL_ID_MAX_LENGTH = 100

DEFAULT_LIMIT = 10
MIN_LIMIT = 1
MAX_LIMIT = 100

DEFAULT_OFFSET = 0
MIN_OFFSET = 0

SIZE_LOGGING_FILES = 5 * 1024 * 1024
COUNT_LOGGING_FILES = 5

TIME_BACKGROUND_TASK = 3


ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "new": {"processing", "error", 'done', 'queued'},
    "processing": {"done", "error", 'new', 'queued'},
    "done": {"processing", "error", 'new', 'queued'},
    "error": {"processing", "new", 'done', 'queued'},
    'queued': {'new', 'processing', 'done', 'error'},
}