import re
from src.constants import (
    MIN_LENGTH_PASSWORD,
    MAX_LENGTH_PASSWORD,
    MIN_LENGTH_USERNAME,
    MAX_LENGTH_USERNAME
)
from src.services.exceptions import (
    InvalidPassword, InvalidUsername
)

USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_.-]+$')


def validate_password(password: str) -> None:
    if not isinstance(password, str):
        raise InvalidPassword('пароль должен быть строкой')
    if len(password) < MIN_LENGTH_PASSWORD:
        raise InvalidPassword(
            f'длина должна быть не меньше {MIN_LENGTH_PASSWORD} символов'
        )
    if len(password) > MAX_LENGTH_PASSWORD:
        raise InvalidPassword(
            f'длина должна быть не больше {MAX_LENGTH_PASSWORD} символов'
        )
    
def validate_username(username: str) -> str:
    if not isinstance(username, str):
        raise InvalidUsername(
            'Некорректный тип username, ожидаемый - строка'
        )
    stripped = username.strip()
    if not stripped:
        raise InvalidUsername(
            f'Некорректный username: {username}, '
            'username не должен состоять из пробелов'
            'или быть пустым'
        )
    if ' ' in stripped:
        raise InvalidUsername('username не может содержать пробелы')
    if not USERNAME_PATTERN.match(stripped):
        raise InvalidUsername(
        f'Некорректный username: {username}'
        'username может содержать только'
        ' буквы, цифры, "_", ".", "-"'
        )
    if len(stripped) < MIN_LENGTH_USERNAME:
        raise InvalidUsername(
            f'длина должна быть не меньше {MIN_LENGTH_USERNAME} символов'
        )
    if len(stripped) > MAX_LENGTH_USERNAME:
        raise InvalidUsername(
            f'длина должна быть не больше {MAX_LENGTH_USERNAME} символов'
        )
    
    return stripped