import os
import uuid
from pathlib import Path
import logging

logger = logging.getLogger('job_processing_service')


class FileStorage:
    """Абстракция над файловой системой для загруженных файлов."""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or os.getenv('UPLOAD_DIR', '/app/files'))

    def save(self, content: bytes, suffix: str) -> str:
        """
        Сохраняет файл, возвращает internal_name.
        """
        self.base_dir.mkdir(parents=True, exist_ok=True)
        internal_name = f'{uuid.uuid4().hex}{suffix}'
        path = self.base_dir / internal_name
        path.write_bytes(content)
        return internal_name


    def delete(self, internal_name: str) -> None:
        path = self.base_dir / internal_name
        try:
            path.unlink()
        except FileNotFoundError:
            logger.warning('Файл уже удален: %s', internal_name)