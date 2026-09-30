from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.database import Base



class FileDB(Base):
    __tablename__ = 'files'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    original_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    internal_name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )  # Внутреннее имя (uuid)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    task_id: Mapped[int] = mapped_column(
        ForeignKey('tasks.id'), nullable=True
    )
    task: Mapped['TaskDB'] = relationship(back_populates='files')
