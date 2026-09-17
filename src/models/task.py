from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime

from src.database import Base
from src.constants import (
    TASK_PRIORITY_DEFAULT
)


class TaskDB(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    text = Column(String, nullable=False)
    status = Column(String, default='new')
    priority = Column(Integer, default=TASK_PRIORITY_DEFAULT)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(
        DateTime, default=datetime.now,
        onupdate=datetime.now,
    )
