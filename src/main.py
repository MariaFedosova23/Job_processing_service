import logging

import uvicorn
from fastapi import FastAPI

from src.api.v1.exception_handlers import register_exception_handlers
from src.api import main_router

logger = logging.getLogger('job_processing_service')
app = FastAPI(title='Job Processing Service')
app.include_router(main_router)
register_exception_handlers(app)

if __name__ == '__main__':
    uvicorn.run('src.main:app', host='0.0.0.0', port=8000)
