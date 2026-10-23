import os
from datetime import timedelta

from authx import AuthXConfig, AuthX

from src.constants import JWT_ACCESS_TOKEN_EXPIRES_IN_MINUTES


jwt_secret_key = os.getenv('JWT_SECRET_KEY')
if not jwt_secret_key:
    raise RuntimeError('JWT_SECRET_KEY не задан в переменных окружения')

auth_config = AuthXConfig()

auth_config.JWT_SECRET_KEY = jwt_secret_key
auth_config.JWT_TOKEN_LOCATION = ['headers']
auth_config.JWT_HEADER_TYPE = 'Bearer'
auth_config.JWT_ACCESS_TOKEN_EXPIRES = timedelta(
    minutes=JWT_ACCESS_TOKEN_EXPIRES_IN_MINUTES
)

security = AuthX(config=auth_config)