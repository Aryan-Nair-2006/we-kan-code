from pydantic import BaseModel, Field, constr
from typing import List, Optional

class QueryRequest(BaseModel):
    question: constr(strip_whitespace=True, min_length=1, max_length=2000) = Field(
        ..., description="The user's question to be answered using project documents."
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
