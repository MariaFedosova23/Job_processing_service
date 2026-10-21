from fastapi import APIRouter

from src.api.v1.tasks import router as tasks_router
from src.api.v1.auth import router as auth_router
from src.api.v1.users import router as users_router
from src.api.v1.router import protected_router, public_router
from src.api.health import router as health_router


public_router.include_router(auth_router)
public_router.include_router(health_router)
protected_router.include_router(tasks_router)
protected_router.include_router(users_router)


main_router = APIRouter()

main_router.include_router(public_router)
main_router.include_router(protected_router)
