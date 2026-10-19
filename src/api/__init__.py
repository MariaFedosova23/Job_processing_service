from fastapi import APIRouter

from src.api.v1.tasks import router as tasks_router
from src.api.v1.users import router as users_router


main_router = APIRouter()

main_router.include_router(tasks_router)
main_router.include_router(users_router)
