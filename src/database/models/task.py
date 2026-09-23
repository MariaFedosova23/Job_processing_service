from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    Enum as SQLENUM, CheckConstraint, String, DateTime, func, Text)

from src.database import Base
from src.constants import (
    TASK_PRIORITY_DEFAULT,
    TASK_PRIORITY_LOW,
    TASK_PRIORITY_HIGH,
    TASK_TITLE_MAX_LENGTH,
    TASK_EXTERNAL_ID_MAX_LENGTH
)
from src.enums import Status


class TaskDB(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            f'priority BETWEEN {TASK_PRIORITY_LOW} AND {TASK_PRIORITY_HIGH}',
            name='ck_tasks_priority_range',
        ),
        CheckConstraint(
            "status IN (" + ", ".join(f"'{s.value}'" for s in Status) + ")",
            name="ck_tasks_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(
        TASK_EXTERNAL_ID_MAX_LENGTH), unique=True, nullable=False
    )
    title: Mapped[str] = mapped_column(
        String(TASK_TITLE_MAX_LENGTH),
        nullable=False
    )
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    status: Mapped[Status] = mapped_column(
        SQLENUM(
            Status,
            native_enum=False,
            values_callable=lambda e: [x.value for x in e]
        ),
        server_default=Status.NEW.value,
        nullable=False, 
        default=Status.NEW
    )
    priority: Mapped[int] = mapped_column(
        default=TASK_PRIORITY_DEFAULT,
        server_default=str(TASK_PRIORITY_DEFAULT),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
