from fastapi import APIRouter

from src.api.v1.tasks import router as tasks_router


main_router = APIRouter()

main_router.include_router(tasks_router)
