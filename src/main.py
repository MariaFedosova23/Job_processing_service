import logging

import uvicorn
from fastapi import FastAPI

from src.api import main_router
from src.core.logging_config import setup_logging


setup_logging()
logger = logging.getLogger('job_processing_service')
app = FastAPI()
app.include_router(main_router)


if __name__ == '__main__':
    uvicorn.run('src.main:app', host='0.0.0.0', port=8000)
