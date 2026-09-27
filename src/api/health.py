
from fastapi import APIRouter, HTTPException, status

import logging
from src.api.v1.dependencies import HealthServiceDep


router = APIRouter(prefix='/health', tags=['health'])

logger = logging.getLogger(__name__)


@router.get('')
async def health_check() -> dict[str, str]:
    """Проверка запуска приложения."""
    result = {'status': 'ok'}
    return result


@router.get('/ready', response_model=None, summary='Проверка доступа')
async def readiness_check(service: HealthServiceDep) -> dict[str, any]:
    """Проверка готовности всех критических зависимостей."""
    result = await service.readiness_check()
    if result['status'] == 'ready':
        return result
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=result
    )
