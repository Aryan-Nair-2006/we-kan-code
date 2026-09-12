from pydantic import BaseModel, Field
from typing import List, Optional

from shared.constants.access_level import AccessLevel


class AuthContext(BaseModel):
    """
    Represents the authenticated identity of a requester.
    Derived server-side from JWT claims (production) or env vars (local dev).
    Never constructed from raw frontend input.
    """
    user_id: str = Field(..., description="Unique identifier for the authenticated user")
    role: str = Field(..., description="Role: public | team | developer | admin")
    access_levels: List[AccessLevel] = Field(
        ...,
        description="Access levels the user is authorized to see, derived server-side"
    )
    team_id: Optional[str] = Field(None, description="Team identifier if applicable")
    email: Optional[str] = Field(None, description="User email — never logged")

    class Config:
        # Prevent accidental mutation
        frozen = True
