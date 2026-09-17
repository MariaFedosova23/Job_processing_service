import pytest

from src.constants import ALLOWED_STATUS_TRANSITIONS


@pytest.mark.parametrize(
    'old_status, new_status',
    [
        (old, new)
        for old, allowed in ALLOWED_STATUS_TRANSITIONS.items()
        for new in allowed
    ],
)
async def test_patch_status(client, old_status, new_status):
    create = await client.post('/api/v1/tasks', json={
        'title': 'Задача',
        'text': 'Описание',
        'priority': 1,
        'external_id': '1c_123',
    })
    task_id = create.json()['id']

    if old_status != 'new':
        await client.patch(
            f'/api/v1/tasks/{task_id}/status',
            json={'status': old_status},
        )

    response = await client.patch(
        f'/api/v1/tasks/{task_id}/status',
        json={'status': new_status},
    )
    assert response.status_code == 200
    assert response.json()['status'] == new_status


async def test_patch_status_invalid_value(client):
    create = await client.post('/api/v1/tasks', json={
        'title': 'Задача',
        'text': 'Описание',
        'priority': 1,
        'external_id': 'invalid_status_test',
    })
    assert create.status_code == 200, create.text
    task_id = create.json()['id']

    response = await client.patch(
        f'/api/v1/tasks/{task_id}/status',
        json={'status': 'totally_wrong'},
    )

    assert response.status_code == 422, response.text