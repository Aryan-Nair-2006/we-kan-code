from pydantic import BaseModel, field_validator
from typing import List, Optional

class IndexedChunk(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    embedding: List[float]
    chunk_index: int
    page_number: Optional[int] = None
    filename: str
    owner: str
    category: str
    access_level: str
    version: str
    document_status: str
    created_at: str
    updated_at: str

    @field_validator('embedding')
    @classmethod
    def check_embedding_not_empty(cls, v):
        if not v:
            raise ValueError("Embedding must not be empty")
        return v

    @field_validator('text')
    @classmethod
    def check_text_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Text must not be empty")
        return v
