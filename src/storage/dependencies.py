
from functools import lru_cache
from src.storage.file_storage import FileStorage


@lru_cache
def get_file_storage() -> FileStorage:
    return FileStorage()