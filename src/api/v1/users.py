import logging 

from fastapi import APIRouter, Depends, HTTPException, status
from authx import TokenPayload
from src.schemas.users import UserLoginSchema, UserLoginResponse
from src.config import security
from src.api.v1.dependencies import get_current_user
from src.database.models.users import UserDB
logger = logging.getLogger('job_processing_service')

router = APIRouter(prefix='/api/v1/auth', tags=['users'])

USERS = {
    'admin': {'password': 'admin123', 'role': 'admin'},
    'user': {'password': 'user1234', 'role': 'user'},
}

@router.post(
    path='/login',
    summary='авторизация пользователя',
    response_model=UserLoginResponse
)
async def create_user(
    creds: UserLoginSchema,

):
    user = USERS.get(creds.username)
    if user and user['password'] == creds.password:
        token = security.create_access_token(
            uid=creds.username,
            data={'role': user['role']}
        )
        
        return {
            'access_token': token, 'token_type': 'bearer'
        }
    raise HTTPException(status_code=401)
    

@router.get('/me')
async def get_me(
    current_user: UserDB = Depends(get_current_user)
):
    return UserDB
#     return {
#         'user_id': payload.sub,
#         'role': payload.extra_dict.get('role'),
#         'expires_at': payload.exp.isoformat() if payload.exp else None,
#     }


# @router