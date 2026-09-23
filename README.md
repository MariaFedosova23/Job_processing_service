# Job Processing Service

Сервис обработки заданий: REST API на FastAPI для создания, отслеживания
и асинхронной обработки задач.

## 🎯 Цель проекта

Предоставить API для управления заданиями (tasks) с жизненным циклом: new - processing - done


Обработка задания выполняется **в фоне** (через `BackgroundTasks`), HTTP-запрос
не блокируется на время «тяжёлой» работы. Клиент получает ответ мгновенно
со статусом `processing`, а через несколько секунд задание переходит в `done`.

## 🏗️ Архитектура

src/
├── main.py # точка входа, создание FastAPI-приложения
├── api/
│ └── v1/
│ ├── tasks.py # роутеры эндпоинтов /api/v1/tasks
│ └── dependencies.py # SessionDep
├── models/
│ └── task.py # SQLAlchemy-модель TaskDB
├── schemas/
│ └── tasks.py # Pydantic-схемы (create/response/status)
├── services/
│ └── task_service.py # бизнес-логика: get_task_or_404, process, set_task_status
├── validators/
│ └── task.py # бизнес-правила (переходы статусов и т.п.)
├── core/
│ ├── logging_config.py # dictConfig для логгера
│ └── logging_filters.py # DefaultFieldsFilter (event, task_id)
├── constants.py # константы (лимиты, переходы статусов, время фона)
└── database.py # engine, AsyncSessionLocal, Base, get_db



### Слои

| Слой | Ответственность |
|---|---|
| **API (routers)** | HTTP: приём запроса, валидация Pydantic, вызов сервисов, ответ |
| **Services** | Бизнес-логика: работа с БД, фоновая обработка, смена статусов |
| **Validators** | Проверки бизнес-правил (допустимые переходы статусов) |
| **Models** | SQLAlchemy-модели (таблицы) |
| **Schemas** | Pydantic-схемы (валидация входа/выхода) |
| **Core** | Логирование, конфигурация |
| **Database** | Подключение к PostgreSQL, фабрика сессий |

### Жизненный цикл задания

GET api/v1`/tasks -> получение всех заданий
GET api/v1/tasks/{task_id} - получение задания по id
POST /api/v1/tasks → new (создание задания со статусом 'new')
POST /api/v1/tasks/{task_id}/process → processing
→ done (через N секунд, в фоне)
PATCH /api/v1/tasks/{task_id}/status → смена статуса (только разрешённые переходы: 'new', 'processing', 'done', 'error')
DELETE /api/v1/tasks/{task_id} → удаление задания


## 🛠️ Стек

- **Python** 3.12
- **FastAPI** — веб-фреймворк
- **SQLAlchemy 2.0** (async) — ORM
- **asyncpg** — асинхронный драйвер PostgreSQL
- **Alembic** — миграции
- **Pydantic v2** — валидация
- **uvicorn** — ASGI-сервер
- **PostgreSQL** 16

## 📦 Требования

- Python 3.12+
- PostgreSQL 16 (или Docker)
- Docker + Docker Compose 

## 🚀 Быстрый старт (Docker)

Самый простой способ — поднять всё через Docker Compose.

### 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd Job_processing_service
```
### 2. Поднять контейнеры

```bash
docker compose up -d --build
```


### 3. Применить миграции

```bash
docker compose exec app alembic upgrade head
```

### 4. Открыть Swagger

http://127.0.0.1:8000/docs

http://127.0.0.1:8000/redoc

### Остановка

```bash
docker compose down          
docker compose down -v
```

## Локальный запуск (без Docker)

### 1. Создать и активировать venv

```bash
python -m venv venv
```
# Windows (Git Bash)
source venv/Scripts/activate

# Linux / macOS
source venv/bin/activate

### 2. Установить зависимости

```bash
pip install -r requirements.txt
```


### 3. Cоздать .env
DATABASE_URL=postgresql+asyncpg://job_user:job_password@localhost:5432/job_db
TEST_DATABASE_URL=postgresql+asyncpg://job_user:job_password@localhost:5432/job_test_db

### 4. Поднять PostgreSQL
```bash
docker compose up -d db
```


### 5. Применить миграции
```bash
alembic upgrade head
```

### 5. Запустить приложение
```bash
python -m src.main
```

### 5. Запустить celery
```bash
celery -A src.worker.app:celery worker --loglevel=info
```

### 6. Запуск postges
```bash
docker run --name postgres-dev \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -p 5432:5432 \
  -d postgres
```