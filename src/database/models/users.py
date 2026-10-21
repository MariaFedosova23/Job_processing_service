from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    CheckConstraint,
    func,
    String,
    DateTime,
    Enum as SQLEnum
)

from src.database import Base
from src.constants import (
    MAX_LENGTH_USERNAME,
    MAX_LENGTH_PASSWORD_HASH
)
from src.enums import Roles

class UserDB(Base):
    __tablename__ = 'users'
    __table_args__ = (
        CheckConstraint(
            "role IN (" + ", ".join(f"'{role.value}'" for role in Roles) + ")",
            name="ck_users_roles",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(
        String(MAX_LENGTH_USERNAME),
        unique=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(MAX_LENGTH_PASSWORD_HASH),
        nullable=False

    )
    
    role: Mapped[Roles] = mapped_column(
        SQLEnum(
            Roles,
            native_enum=False,
            values_callable=lambda e: [x.value for x in e]
        ),
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False
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
    tasks: Mapped[list['TaskDB']] = relationship(
        back_populates='owner',
        cascade='all, delete-orphan',
    )