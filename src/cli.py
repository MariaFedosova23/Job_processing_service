import asyncio
import getpass
from typing import Optional

import typer

from src.database import AsyncSessionLocal
from src.database.models.users import UserDB
from src.database.repositories.user import UserRepository
from src.enums import Roles
from src.services.user_service import UserService
from src.services.exceptions import UserAlreadyExists
from src.services.validator_user import (
    validate_password,
    validate_username,
    InvalidUsername, InvalidPassword
)

app = typer.Typer(help='Управление пользователями Job Processing Service')

async def async_create_admin(username: str, password: str) -> UserDB:
    """Создаёт администратора."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        service = UserService(repo)
        return await service.create_user(
            username=username,
            password=password,
            role=Roles.ADMIN,
        )

@app.command()
def create_admin(
    username: str = typer.Option(
        ..., '--username', '-u', prompt=True, help='Имя администратора'
    ),
    password: Optional[str] = typer.Option(
        None, '--password', '-p', help='Пароль (если не указан, будет запрошен скрыто)'
    ),
):
    try:
        username = validate_username(username)
    except InvalidUsername as exc:
        typer.secho(f'Ошибка: {exc}', fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    
    if password is None:
        password = getpass.getpass('Пароль: ')
        password_confirm = getpass.getpass('Повторите пароль: ')
        if password != password_confirm:
            typer.secho('Пароли не совпадают', fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
    try:
        validate_password(password)
    except InvalidPassword as exc:
        typer.secho(f'Ошибка: {exc}', fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
        
    try:
        user = asyncio.run(async_create_admin(username, password))
    except UserAlreadyExists as exc:
        typer.secho(f'Ошибка: {exc}', fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    except Exception as exc:
        typer.secho(f'Ошибка БД: {exc}', fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.secho(
        f"Администратор '{user.username}' успешно создан (id={user.id})",
        fg=typer.colors.GREEN,
    )





if __name__ == '__main__':
    app()



