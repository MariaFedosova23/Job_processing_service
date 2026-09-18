
from src.database.models.task import TaskDB


def make_tasks():
    return [
        TaskDB(title='Новая', text='...', priority=1,
               external_id='f_new_1', status='new'),
        TaskDB(title='Новая 2', text='...', priority=1,
               external_id='f_new_2', status='new'),
        TaskDB(title='В работе', text='...', priority=1,
               external_id='f_proc_1', status='processing'),
        TaskDB(title='Готова', text='...', priority=1,
               external_id='f_done_1', status='done'),
    ]


async def test_filter_by_status(client, db_session):
    db_session.add_all(make_tasks())
    await db_session.commit()
    response = await client.get(
        '/api/v1/tasks', params={'status': 'processing'}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) == 1
    assert data[0]['external_id'] == 'f_proc_1'
    assert data[0]['status'] == 'processing'


async def test_no_filter_returns_all(client, db_session):
    db_session.add_all(make_tasks())
    await db_session.commit()

    response = await client.get('/api/v1/tasks')
    assert response.status_code == 200, response.text

    data = response.json()
    assert len(data) == 4