import os
from authx import AuthXConfig, AuthX

jwt_secret_key = os.getenv('JWT_SECRET_KEY')
if not jwt_secret_key:
    raise RuntimeError('JWT_SECRET_KEY не задан в переменных окружения')

auth_config = AuthXConfig()

auth_config.JWT_SECRET_KEY = jwt_secret_key
auth_config.JWT_TOKEN_LOCATION = ['headers']
auth_config.JWT_HEADER_TYPE = 'Bearer'


security = AuthX(config=auth_config)