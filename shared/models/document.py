from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from shared.constants.access_level import AccessLevel
from shared.constants.document_status import DocumentStatus

class DocumentMetadata(BaseModel):
    document_id: str
    filename: str
    file_type: str
    owner: str
    category: str
    created_at: str
    updated_at: str
    version: str
    access_level: AccessLevel
    status: DocumentStatus
    indexing_status: str = "NOT_INDEXED"
    s3_key: Optional[str] = None
    chunk_count: Optional[int] = 0
    processing_error: Optional[str] = None

class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int
    text: str
    page_number: Optional[int] = None
    filename: str
    
class QuestionRequest(BaseModel):
    question: str
    access_levels: List[AccessLevel] = Field(default_factory=lambda: [AccessLevel.PUBLIC])
    
class SourceReference(BaseModel):
    document_id: str
    filename: str
    page_number: Optional[int]
    supporting_passage: str
    owner: str
    version: str
    
class AnswerResponse(BaseModel):
    answer: str
    sources: List[SourceReference] = []
    confidence: Optional[float] = None
    abstaining: bool = False
    
class FlagRequest(BaseModel):
    document_id: str
    chunk_id: Optional[str]
    reason: str
    
class ReviewRecord(BaseModel):
    flag_id: str
    document_id: str
    reviewer: str
    action_taken: str
    updated_at: str
