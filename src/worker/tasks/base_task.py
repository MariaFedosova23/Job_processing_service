# from celery import Task
# from database.database import AsyncSessionLocal

# class DatabaseTask(Task):
#     """
#     Кастомный базовый класс задачи Celery.
#     Автоматически создаёт и закрывает сессию SQLAlchemy для каждой задачи.
#     """
#     _session = None

#     @property
#     def session(self):
#         """Ленивая инициализция сессии."""
#         if self._session is None:
#             self._session = AsyncSessionLocal()
#         return self._session

#     def after_return(self, *args, **kwargs):
#         """Вызывается Celery после завершения задачи (успех или ошибка)."""
#         if self._session is not None:
#             self._session.close()
#             self._session = None
#         super().after_return(*args, **kwargs)


# engine = create_async_engine(
#     DATABASE_URL,
#     echo=True
# )

# session: async_sessionmaker[AsyncSession] = async_sessionmaker(
#     engine,
#     expire_on_commit=False
# )

# loop = asyncio.get_event_loop()


# @asynccontextmanager
# async def scoped_session():
#     scoped_factory = async_scoped_session(
#         session,
#         scopefunc=current_task,
#     )
#     try:
#         async with scoped_factory() as s:
#             yield s
#     finally:
#         await scoped_factory.remove()

# async with scoped_session() as s:
#     await s.execute(...)

# @shared_task(
#     bind=True,
#     name='celery:test'
# )
# def test_task(self, data: dict, prices: dict):
#   result = loop.run_until_complete(здесь_ваша_асинхнонная_функция(и, аргументы))
#   return result