from fastapi import HTTPException, Depends
from authx import TokenPayload

from src.config import security


def require_scopes(*scopes: str, all_required: bool = True):
    async def checker(payload: TokenPayload = Depends(security.access_token_required)):
        if not payload.has_scopes(*scopes, all_required=all_required):
            raise HTTPException(403, "Недостаточно прав")
        return payload
    return checker


def get_current_user(
    payload: TokenPayload = Depends(security.access_token_required)
):
    return {'id': payload.sub}


# временно
async def get_owned_task(
    task_id: int,
    payload: TokenPayload = Depends(security.access_token_required),
    db: Session = Depends(get_db)
) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Задача не найдена")
    # Сравниваем ID владельца задачи с ID из токена (поле sub)
    if str(task.owner_id) != payload.sub:
        raise HTTPException(403, "Это не ваша задача")
    return task