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
    # Phase 7: Freshness / versioning fields
    content_hash: Optional[str] = None       # SHA-256 of raw uploaded bytes
    indexed_at: Optional[str] = None         # ISO timestamp when indexing completed
    superseded_by: Optional[str] = None      # document_id of the newer version
    is_current: bool = True                  # False when a newer version exists

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
    chunk_id: Optional[str] = None
    reason: str
    flagged_by: str = "anonymous"

class FlagRecord(BaseModel):
    flag_id: str
    document_id: str
    chunk_id: Optional[str] = None
    reason: str
    flagged_by: str = "anonymous"
    status: str = "OPEN"  # OPEN | RESOLVED
    created_at: str
    resolved_at: Optional[str] = None
    resolution: Optional[str] = None
    reviewer: Optional[str] = None
    notes: Optional[str] = None

class ResolveFlagRequest(BaseModel):
    resolution: str  # e.g. "CORRECTED", "DISMISSED", "ARCHIVE_DOCUMENT"
    reviewer: str = "anonymous"
    notes: Optional[str] = None

class ReviewRecord(BaseModel):
    flag_id: str
    document_id: str
    reviewer: str
    action_taken: str
    updated_at: str

# ---------------------------------------------------------------------------
# Phase 7: Conflict Detection
# ---------------------------------------------------------------------------

class ConflictRecord(BaseModel):
    """
    Represents a detected semantic conflict between two document chunks.
    Stored in the ConflictsTable DynamoDB table.
    """
    conflict_id: str
    source_document_id: str
    source_chunk_id: str
    conflicting_document_id: str
    conflicting_chunk_id: str
    relationship: str = "CONTRADICTS"
    confidence: float
    topic: Optional[str] = None           # Brief reason from the classifier
    detected_at: str
    status: str = "OPEN"                  # OPEN | REVIEWED | RESOLVED | DISMISSED
    reviewed_by: Optional[str] = None
    resolution: Optional[str] = None
