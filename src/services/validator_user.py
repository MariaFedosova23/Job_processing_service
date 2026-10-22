from src.constants import MIN_LENGTH_PASSWORD, MAX_LENGTH_PASSWORD
from src.services.exceptions import InvalidPassword


def validate_password(password: str) -> None:
    if len(password) < MIN_LENGTH_PASSWORD:
        raise InvalidPassword(
            f'длина должна быть не меньше {MIN_LENGTH_PASSWORD} символов'
        )
    if len(password) > MAX_LENGTH_PASSWORD:
        raise InvalidPassword(
            f'длина должна быть не больше {MAX_LENGTH_PASSWORD} символов'
        )
