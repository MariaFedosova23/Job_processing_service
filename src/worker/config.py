import os

BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/' )
RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

TASK_SERIALIZER = "json"
RESULT_SERIALIZER = "json"
ACCEPT_CONTENT = ["json"]
TIMEZONE = "UTC"
ENABLE_UTC = True

# Опционально: маршрутизация задач по очередям
TASK_ROUTES = {
    "worker.tasks.tasks.process_task": {"queue": "default"},
    # "worker.tasks.reports.generate_report": {"queue": "reports"},
}
