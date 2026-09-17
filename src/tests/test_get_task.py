from src.models.task import TaskDB


async def test_get_task_not_found(client):
    response = await client.get('/api/v1/tasks/999999999')
    assert response.status_code == 404


async def test_get_task_success(client, db_session):

    task = TaskDB(
        title='Задача',
        text='Описание',
        priority=3,
        external_id='get_ok',
        status='new',
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    response = await client.get(f'/api/v1/tasks/{task.id}')
    assert response.status_code == 200, response.text

    data = response.json()
    assert data['id'] == task.id
    assert data['title'] == 'Задача'
    assert data['text'] == 'Описание'
    assert data['priority'] == 3
    assert data['external_id'] == 'get_ok'
    assert data['status'] == 'new'