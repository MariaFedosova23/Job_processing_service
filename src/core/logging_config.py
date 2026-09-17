import logging.config
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[2] / 'logs'
LOG_DIR.mkdir(exist_ok=True)

from src.constants import SIZE_LOGGING_FILES, COUNT_LOGGING_FILES

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'app': {
            'format': (
                '[%(asctime)s] %(levelname)-8s | %(event)s | '
                'task_id=%(task_id)s | %(message)s'
            ),
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'default': {
            'format': '[%(asctime)s] %(levelname)-8s | %(name)s | %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },

    'filters': {
        'default_fields': {
            '()': 'src.core.logging_filters.DefaultFieldsFilter',
        },
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'app',
            'filters': ['default_fields'],
            'stream': 'ext://sys.stdout',
            'level': 'INFO',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'app',
            'filters': ['default_fields'],
            'filename': str(LOG_DIR / 'app.log'),
            'maxBytes': SIZE_LOGGING_FILES,
            'backupCount': COUNT_LOGGING_FILES,
            'encoding': 'utf-8',
            'level': 'DEBUG',
        },
        'errors_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'default',
            'filename': str(LOG_DIR / 'errors.log'),
            'maxBytes': SIZE_LOGGING_FILES,
            'backupCount': COUNT_LOGGING_FILES,
            'encoding': 'utf-8',
            'level': 'ERROR',
        },
    },

    'loggers': {
        'job_processing_service': {
            'handlers': ['console', 'file', 'errors_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },

    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}


def setup_logging() -> None:
    logging.config.dictConfig(LOGGING_CONFIG)