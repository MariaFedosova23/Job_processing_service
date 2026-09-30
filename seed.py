import asyncio
from datetime import datetime, timezone

from src.database.database import get_session
from src.database.models.task import TaskDB


SEED_TASKS = [
    {
        'title': 'Products',
        'text': 'go to shop',
        'priority': 2,
        'external_id': 'products_shopping',
    },
    {
        'title': 'Cooking',
        'text': 'cook a salad',
        'priority': 3,
        'external_id': 'cooking_salad',
    },
    {
        'title': 'Cleaning',
        'text': 'clean a room',
        'priority': 4,
        'external_id': 'cleaning_room',
    },
    {
        'title': 'Doing homework',
        'text': 'math and english',
        'priority': 1,
        'external_id': 'homework_isd',
    },
        {
        'title': 'English essay',
        'text': 'write 500 words about my favourite book',
        'priority': 1,
        'external_id': 'homework_english_essay',
    },
    {
        'title': 'Pay utility bills',
        'text': 'electricity, water, internet',
        'priority': 1,
        'external_id': 'bills_utilities',
    },
    {
        'title': 'Call dentist',
        'text': 'schedule checkup for next week',
        'priority': 2,
        'external_id': 'call_dentist',
    },
    {
        'title': 'Fix leaking tap',
        'text': 'replace washer in bathroom sink',
        'priority': 3,
        'external_id': 'fix_tap_bathroom',
    },
    {
        'title': 'Read a book',
        'text': 'finish chapter 7 of "Clean Code"',
        'priority': 5,
        'external_id': 'read_clean_code',
    },
    {
        'title': 'Water plants',
        'text': 'living room and balcony flowers',
        'priority': 4,
        'external_id': 'water_plants',
    },
    {
        'title': 'Plan weekend trip',
        'text': 'choose route, book hotel, check weather',
        'priority': 2,
        'external_id': 'plan_weekend_trip',
    },
    {
        'title': 'Update resume',
        'text': 'add latest project and skills',
        'priority': 2,
        'external_id': 'update_resume',
    },
    {
        'title': 'Backup laptop',
        'text': 'copy photos and documents to external drive',
        'priority': 3,
        'external_id': 'backup_laptop',
    },
    {
        'title': 'Learn Python decorators',
        'text': 'read docs and write two examples',
        'priority': 1,
        'external_id': 'learn_python_decorators',
    },
    {
        'title': 'Practice SQL joins',
        'text': 'inner, left, right, full — 10 queries',
        'priority': 1,
        'external_id': 'practice_sql_joins',
    },
    {
        'title': 'Write unit tests',
        'text': 'cover service layer with pytest',
        'priority': 2,
        'external_id': 'write_unit_tests',
    },
    {
        'title': 'Refactor task service',
        'text': 'split large methods into smaller ones',
        'priority': 3,
        'external_id': 'refactor_task_service',
    },
    {
        'title': 'Review pull request',
        'text': 'check logic, tests, and style',
        'priority': 1,
        'external_id': 'review_pr_42',
    },
    {
        'title': 'Prepare presentation',
        'text': 'slides for Monday standup',
        'priority': 2,
        'external_id': 'prepare_standup_slides',
    },
    {
        'title': 'Meditate',
        'text': '10 minutes of breathing practice',
        'priority': 5,
        'external_id': 'meditate_daily',
    },
    
        
]


async def seed():
    async with get_session() as session:
        for data in SEED_TASKS:
            from src.database.repositories.task import TaskRepository
            repo = TaskRepository(session)
            existing = await repo.get_by_external_id(data['external_id'])
            if existing:
                print(f'skip {data["external_id"]}: already exists')
                continue

            task = TaskDB(**data)
            session.add(task)
            print(f"created {data['external_id']}")
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())