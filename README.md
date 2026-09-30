# Job Processing Service

Сервис обработки заданий: REST API на FastAPI для создания, отслеживания
и асинхронной обработки задач.

## 🎯 Цель проекта

Предоставить API для управления заданиями (tasks) с жизненным циклом: new - processing - done

Обработка задания выполняется **в фоне** (через `BackgroundTasks`), HTTP-запрос
не блокируется на время «тяжёлой» работы. Клиент получает ответ мгновенно
со статусом `processing`, а через несколько секунд задание переходит в `done`.

## 🏗️ Архитектура

📦 Job Processing Service

│

├── 🚀 main.py                      # Точка входа: создание FastAPI-приложения

│

├── 🌐 api/

│   └── v1/

│       ├── tasks.py                # Роутеры эндпоинтов /api/v1/tasks

│       └── dependencies.py         # SessionDep (зависимость сессии БД)

│

├── 🗄️ models/

│   └── task.py                     # SQLAlchemy-модель TaskDB

│   └── file.py

├── 📋 schemas/

│   └── tasks.py                    # Pydantic-схемы

│   └── files.py

├── ⚙️ services/

│   └── task_service.py             # Бизнес-логика:

│

├── ✅ validators/

│   └── task.py                     # Бизнес-правила (переходы статусов и т.п.)

│

├── 🧰 core/

│   ├── logging_config.py           # dictConfig для логгера

│   └── logging_filters.py          # DefaultFieldsFilter (event, task_id)

│

├── 📌 constants.py                 # Константы: лимиты, переходы статусов, время фона

└── 🗃️ database.py                  # engine, AsyncSessionLocal, Base, get_db

### Слои

| Слой | Ответственность |
| --- | --- |
| **API (routers)** | HTTP: приём запроса, валидация Pydantic, вызов сервисов, ответ |
| **Services** | Бизнес-логика: работа с БД, фоновая обработка, смена статусов |
| **Validators** | Проверки бизнес-правил (допустимые переходы статусов) |
| **Models** | SQLAlchemy-модели (таблицы) |
| **Schemas** | Pydantic-схемы (валидация входа/выхода) |
| **Core** | Логирование, конфигурация |
| **Database** | Подключение к PostgreSQL, фабрика сессий |
| **Worker** | Celery |

### Жизненный цикл задания

GET api/v1`/tasks -> получение всех заданий
GET api/v1/tasks/{task_id} - получение задания по id

POST /api/v1/tasks → new (создание задания со статусом 'new')

PATCH /api/v1/tasks/{task_id}/status → смена статуса (только разрешённые переходы: 'new', 'processing', 'done', 'error')

POST /api/v1/tasks/{task_id}/process: new → queue → processing → done/error

POST /api/v1/tasks/{task_id}/retry: error → queue → processing → done/error

POST /api/v1/tasks/{task_id}/cancel: queue → cancel | processing → cancel

POST /api/v1/tasks/{task_id}/files -> загрузка файла

DELETE /api/v1/tasks/{task_id} → удаление задания

## 🛠️ Стек

- **Python** 3.12
- **FastAPI** — веб-фреймворк
- **SQLAlchemy 2.0.52** (async) — ORM
- **asyncpg** — асинхронный драйвер PostgreSQL
- **Alembic** — миграции
- **Pydantic v2** — валидация
- **uvicorn** — ASGI-сервер
- **PostgreSQL** 15
- **celery** 15.6.3
- **redis** 8.1.0

## 📦 Требования

- Python 3.12+
- PostgreSQL 15 (или Docker)
- Docker + Docker Compose

## 🗃️ Таблица `tasks` и `task_result`

## Почему результат вынесен в отдельную таблицу `task_result`
`
1. **Разделение ответственности** — не смешиваем результат с самой задачей.
2. **Размер** — таблица `tasks` остаётся лёгкой.
3. **Запросы списка задач** — не тянут результат, когда он не нужен.

## 🔄 Retry в Celery

### Что это

Celery по сигналу исключения решает повторить доставку **того же сообщения** с тем же `task_id` и заново отправляет его воркеру.

Retry срабатывает, когда таска:

- выбросила исключение,
- была убита воркером,
- превысила таймаут
- упала вместе с воркером.
- Retry vs повторный вызов API
- |  | Retry | Повторный вызов API |
| --- | --- | --- |
| Кто инициирует | Система (Celery) | Клиент |
| Причина | Внутренний сбой | Действие пользователя |

Это разные вещи: retry — реакция системы на сбой, повторный вызов API — действие клиента.
- ### Когда retry уместен

- **Ошибка транзиентная** — при повторе, скорее всего, пройдёт (сеть, БД, внешний API).
- **Есть смысл ждать** — например, внешний сервис временно недоступен и вернётся.
- **Задача идемпотентна** — повтор не создаст дублей.

**Общий признак:** состояние системы изменится к моменту ретрая.
- ### Когда retry бессмысленен

- **Ошибка детерминированная** — невалидные данные, запрещённые слова.
- **Повтор не изменит результат** — баг в коде, `ValueError`, `KeyError`.
- **Задача не идемпотентна** — повтор приведёт к дублям.
`

## 🚀 Быстрый старт (Docker)

Самый простой способ — поднять всё через Docker Compose.

### 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd Job_processing_service
```
### 2. Cоздать .env

### 3. Поднять контейнеры

```bash
docker compose up -d --build
```


### 4. Запустить тестовые данные(опционально)
```bash
docker compose --profile seed run --rm seed
```


### 5. Открыть Swagger

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

[http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

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

### 7. Запустить flower

```bash
celery -A src.worker.app:celery flower --port=5555
```

## 🧪 Запуск тестов
Создать тестовую базу:
docker compose exec postgres psql -U user -d job_processing_service -c 'CREATE DATABASE job_service_test'

```bash
docker compose run --rm tests 
  
```
