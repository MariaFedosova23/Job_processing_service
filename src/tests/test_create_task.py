import pytest

from src.constants import (
    TASK_PRIORITY_LOW,
    TASK_PRIORITY_HIGH,
    TASK_PRIORITY_DEFAULT,
)


async def test_create_task_success(client):
    response = await client.post('/api/v1/tasks', json={
        'title': 'Тест',
        'text': 'Описание',
        'priority': 1,
        'external_id': '1c_123',
    })
    assert response.status_code == 200


async def test_create_task_duplicate_external_id(client):
    payload = {
        'title': 'Тест',
        'text': 'проверка уникальности поля external_id',
        'priority': 2,
        'external_id': '1c_124',
    }
    response = await client.post('/api/v1/tasks', json=payload)
    assert response.status_code == 200

    response = await client.post('/api/v1/tasks', json=payload)
    assert response.status_code == 409


@pytest.mark.parametrize('valid_priority', [
    TASK_PRIORITY_LOW,
    TASK_PRIORITY_HIGH,
    TASK_PRIORITY_DEFAULT,
])
async def test_create_task_valid_priority(client, valid_priority):
    response = await client.post('/api/v1/tasks', json={
        'title': 'Задача',
        'text': 'Описание',
        'priority': valid_priority,
        'external_id': f'1c_123_{valid_priority}',
    })
    assert response.status_code == 200, response.text

    task_id = response.json()['id']

    check = await client.get(f'/api/v1/tasks/{task_id}')
    assert check.json()['priority'] == valid_priority