from fastapi import APIRouter, Depends
from src.api.v1.dependencies import get_current_user

public_router = APIRouter()

protected_router = APIRouter(
    dependencies=[Depends(get_current_user)]
)
