import logging


class DefaultFieldsFilter(logging.Filter):
    """Подставляет значения по умолчанию для полей,
    которые могут отсутствовать в extra."""

    DEFAULTS = {
        'event': '-',
        'task_id': '-',
    }

    def filter(self, record: logging.LogRecord) -> bool:
        for field, default in self.DEFAULTS.items():
            if not hasattr(record, field):
                setattr(record, field, default)
        return True