import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from backend.app.core.logging import setup_logger

logger = setup_logger(__name__)

class FlagSubmission(BaseModel):
    flag_id: str = Field(default_factory=lambda: f"FLAG-{uuid.uuid4().hex[:8]}")
    document_id: Optional[str] = "DOC-UNKNOWN"
    chunk_id: Optional[str] = None
    reason: str
    details: Optional[str] = ""
    question: Optional[str] = ""
    answer: Optional[str] = ""
    source_filename: Optional[str] = "Unknown"
    supporting_passage: Optional[str] = ""
    status: str = "Pending"  # Pending, Under Review, Resolved, Rejected
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ReviewUpdateRequest(BaseModel):
    status: str
    reviewer: Optional[str] = "Admin"
    notes: Optional[str] = None

# In-memory store fallback for hackathon / local development, can interface with DynamoDB
_REVIEWS_DB: Dict[str, FlagSubmission] = {}

class ReviewService:
    def create_flag(self, flag: FlagSubmission) -> FlagSubmission:
        _REVIEWS_DB[flag.flag_id] = flag
        logger.info(f"Created review flag {flag.flag_id} for document {flag.document_id}")
        return flag

    def list_flags(self, status_filter: Optional[str] = None) -> List[FlagSubmission]:
        flags = list(_REVIEWS_DB.values())
        if status_filter and status_filter != "All":
            flags = [f for f in flags if f.status.lower() == status_filter.lower()]
        # Return sorted by created_at descending
        flags.sort(key=lambda x: x.created_at, reverse=True)
        return flags

    def update_flag_status(self, flag_id: str, update_req: ReviewUpdateRequest) -> Optional[FlagSubmission]:
        if flag_id not in _REVIEWS_DB:
            return None
        flag = _REVIEWS_DB[flag_id]
        flag.status = update_req.status
        flag.updated_at = datetime.now(timezone.utc).isoformat()
        _REVIEWS_DB[flag_id] = flag
        logger.info(f"Updated flag {flag_id} status to {update_req.status}")
        return flag
