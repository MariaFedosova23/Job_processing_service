from pathlib import Path
import logging

from src.database.repositories.outbox import OutboxRepository
from src.database.repositories.task import TaskRepository
from src.database.models.file import FileDB
from src.services.exceptions import TaskNotFoundError
from src.services.validator_task import (
    validate_file_type,
    validate_file_size,
)
from src.storage.file_storage import FileStorage
from src.constants import CELERY_TASK_GET_FILE_NAME

logger = logging.getLogger('job_processing_service')



class FileService:
    def __init__(self, repo: TaskRepository, storage: FileStorage):
        self.repo = repo 
        self.storage = storage

    async def upload_file(
        self,
        task_id: int,
        *,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> FileDB:

        validate_file_type(content_type)
        validate_file_size(len(content))
        
        suffix = Path(filename).suffix or '.bin'
        internal_name = self.storage.save(content, suffix)
        
        try:
         
            file_db = await self.repo.create_file_with_outbox(
                task_id=task_id,
                original_name=filename,
                internal_name=internal_name,
                mime_type=content_type,
                size_bytes=len(content),
            )
            if file_db is None:
                raise TaskNotFoundError(task_id)
            
            
        except Exception as exc:
            logger.exception(
                'Не удалось сохранить информацию о загруженном файле в БД.'
                'Ошибка: %s', str(exc)
            )
            self.storage.delete(internal_name)
            raise


        logger.info(
            "Файл загружен: task_id=%s, file_id=%s, internal_name=%s",
            task_id, file_db.id, internal_name,
            extra={"event": "file_uploaded", "task_id": task_id, "file_id": file_db.id},
        )
        return file_db