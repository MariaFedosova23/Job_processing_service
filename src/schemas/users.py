from pydantic import BaseModel, ConfigDict, Field
from src.enums import Roles
from src.constants import MIN_LENGTH_PASSWORD

class UserLoginSchema(BaseModel):
    username: str
    password: str = Field(
        min_length=MIN_LENGTH_PASSWORD
    )

class UserRead:
    id: int
    username: str
    role: Roles
    is_active: bool


class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str