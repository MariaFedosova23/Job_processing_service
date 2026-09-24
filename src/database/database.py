import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager


load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv('DATABASE_URL')

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("SQLALCHEMY_DATABASE_URL не установлена!")

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
)

engine_worker = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=NullPool,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

AsyncSessionWorker = async_sessionmaker(
    bind=engine_worker,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_session() -> AsyncSession:
    async with AsyncSessionWorker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise