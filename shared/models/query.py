from pydantic import BaseModel, Field, constr
from typing import List, Optional

from shared.constants.access_level import AccessLevel

class QueryRequest(BaseModel):
    question: constr(strip_whitespace=True, min_length=1, max_length=2000) = Field(
        ..., description="The user's question to be answered using project documents."
    )
    access_levels: List[AccessLevel] = Field(
        default_factory=lambda: [AccessLevel.PUBLIC],
        description="Access levels the requester is cleared to see. "
                    "NOTE (Phase 7): In production, these are OVERRIDDEN by the server-side "
                    "AuthContext derived from JWT claims. Frontend-supplied values are only "
                    "used as a fallback in local development mode."
    )

class SourceCitation(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    filename: Optional[str] = None
    page_number: Optional[int] = None
    owner: Optional[str] = None
    category: Optional[str] = None
    access_level: Optional[str] = None
    version: Optional[str] = None
    similarity: float = Field(..., ge=0.0, le=1.0)
    
class QueryResponse(BaseModel):
    question: str
    answer: str
    grounded: bool
    confidence: float = 0.0
    sources: List[SourceCitation] = Field(default_factory=list)
    # Phase 7: Conflict and audit fields
    conflict_warning: bool = False
    conflict_details: Optional[str] = None
    user_id: Optional[str] = None         # Populated from AuthContext for audit trail
