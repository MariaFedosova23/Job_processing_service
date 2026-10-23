from pydantic import BaseModel, Field, field_validator
from src.enums import Roles
from src.constants import (
    MIN_LENGTH_PASSWORD,
    MAX_LENGTH_PASSWORD,
    MAX_LENGTH_USERNAME,
    MIN_LENGTH_USERNAME
)
from src.services.validator_user import (
    validate_username,
    InvalidUsername
)

class UserLoginSchema(BaseModel):
    username: str = Field(
        min_length=MIN_LENGTH_USERNAME,
        max_length=MAX_LENGTH_USERNAME,
    )
    password: str = Field(
        min_length=MIN_LENGTH_PASSWORD,
        max_length=MAX_LENGTH_PASSWORD,
    )
    @field_validator('username')
    @classmethod
    def _validate_username(cls, value: str) -> str:
        try:
            return validate_username(value)
        except InvalidUsername as exc:
            raise ValueError(str(exc))



class UserResponseSchema(BaseModel):
    id: int
    username: str
    role: Roles
    is_active: bool = True


class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'

class CurrentUserSchema(UserResponseSchema):
    pass


class CreateUserSchema(BaseModel):
    username: str = Field(
        max_length=MAX_LENGTH_USERNAME,
        min_length=MIN_LENGTH_USERNAME
    )
    password: str = Field(
        min_length=MIN_LENGTH_PASSWORD,
        max_length=MAX_LENGTH_PASSWORD,
    )
    role: Roles

    @field_validator('username')
    @classmethod
    def _validate_username(cls, value: str) -> str:
        try:
            return validate_username(value)
        except InvalidUsername as exc:
            raise ValueError(str(exc))



class PatchUserSchema(BaseModel):
    role: Roles | None = None
    is_active: bool | None = None


class ChangePasswordSchema(BaseModel):
    old_password: str = Field(
        min_length=MIN_LENGTH_PASSWORD,
        max_length=MAX_LENGTH_PASSWORD,
    )
    new_password: str = Field(
        min_length=MIN_LENGTH_PASSWORD,
        max_length=MAX_LENGTH_PASSWORD,
    )

class ResetPasswordSchema(BaseModel):
    new_password: str = Field(
        min_length=MIN_LENGTH_PASSWORD,
        max_length=MAX_LENGTH_PASSWORD,
    )