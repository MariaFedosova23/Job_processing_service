from pydantic import BaseModel


class FileResponse(BaseModel):
    id: int
    original_name: str
    internal_name: str
    mime_type: str
    size_bytes: int

    class Config:
        from_attributes = True
