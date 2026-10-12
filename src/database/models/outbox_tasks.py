from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    Enum as SQLENUM,
    String, DateTime,
    func,
    Text,
    Integer,
    Index,
    text
)
from sqlalchemy.dialects.postgresql import JSONB
from src.database import Base
from src.constants import (
    MAX_IDEMPOTENCY_KEY,
    MAX_TASK_NAME,
)
from src.enums import OutboxStatus


class OutboxTaskDB(Base):
    __tablename__ = 'outbox_tasks'
    __table_args__ = (
        Index(
            'ix_outbox_tasks_ready',
            'status',
            'next_retry_at',
            'created_at',
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_name: Mapped[str] = mapped_column(String(MAX_TASK_NAME), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[OutboxStatus] = mapped_column(
        SQLENUM(
            OutboxStatus,
            name='outbox_status',
            native_enum=True,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=OutboxStatus.PENDING,
        server_default=OutboxStatus.PENDING.value
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(
        MAX_IDEMPOTENCY_KEY),
        unique=True,
        nullable=True
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default='0'
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

