import logging 

from fastapi import APIRouter, Depends, HTTPException, status
from authx import TokenPayload
from src.schemas.users import UserLoginSchema, UserLoginResponse, CurrentUserSchema
from src.config import security
from src.api.v1.dependencies import get_current_user
from src.database.models.users import UserDB
from src.auth.permissions import get_scopes_for_role
from src.api.v1.dependencies import UserServiceDep

logger = logging.getLogger('job_processing_service')

router = APIRouter(prefix='/api/v1/auth', tags=['auth'])

USERS = {
    'admin': {'password': 'admin123', 'role': 'admin'},
    'user': {'password': 'user1234', 'role': 'user'},
}

@router.post(
    path='/login',
    summary='Авторизация пользователя',
    response_model=UserLoginResponse
)
async def login_user(
    creds: UserLoginSchema,
    service: UserServiceDep,

):
    user = await service.authenticate(creds.username, creds.password)
    
    token = security.create_access_token(
        uid=str(user.id),
        data={'role': user.role.value},
        scopes=get_scopes_for_role(user.role.value),
    )
    return UserLoginResponse(access_token=token)
    

@router.get(
    '/me',
    summary='Получение текущего пользователя',
    response_model=CurrentUserSchema
)
async def get_me(
    current_user: UserDB = Depends(get_current_user)
):
    return current_user
