from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import sys
import os
import time

# Add parent dir to path to allow importing shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.core.logging import setup_logger, generate_request_id, log_structured

logger = setup_logger("api_main")

from backend.app.api.documents import router as documents_router
from backend.app.api.endpoints import analytics

app = FastAPI(title="Team Knowledge Finder API", version="0.1.0")

app.include_router(documents_router)
app.include_router(analytics.router)

@app.get("/health")
def health_check():
    logger.info("Health check endpoint called")
    return {"status": "ok", "service": "team-knowledge-finder"}

from shared.models.query import QueryRequest, QueryResponse
from shared.models.document import (
    FlagRequest, FlagRecord, ResolveFlagRequest, ConflictRecord, DocumentMetadata
)
from backend.app.services.query_service import QueryService
from backend.app.services.review_service import ReviewService
from backend.app.services.conflict_service import ConflictService
from backend.app.services.authorization_service import AuthorizationService, get_required_auth_context
from backend.app.core.exceptions import ValidationError
from backend.app.models.auth import AuthContext
from fastapi import HTTPException
from typing import List, Optional

review_service = ReviewService()
auth_service = AuthorizationService()

# ---------------------------------------------------------------------------
# Phase 7: Authentication endpoint
# ---------------------------------------------------------------------------

@app.get("/auth/me", response_model=dict)
def get_auth_me(request: Request):
    """
    Returns the current user's AuthContext.
    In local dev (ENVIRONMENT=local): uses DEV_USER_ID / DEV_ROLE env vars.
    In production: parses JWT from Authorization header.
    """
    try:
        ctx = get_required_auth_context(request)
        return {
            "user_id": ctx.user_id,
            "role": ctx.role,
            "access_levels": [lvl.value for lvl in ctx.access_levels],
            "team_id": ctx.team_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building auth context: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

@app.post("/query", response_model=QueryResponse)
def query_knowledge(request: QueryRequest, http_request: Request):
    request_id = generate_request_id()
    try:
        # Phase 7: Build AuthContext server-side — override frontend-supplied access levels
        auth_ctx = get_required_auth_context(http_request)

        svc = QueryService()
        response = svc.query(request, auth_context=auth_ctx)
        return response
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_structured(logger, "error", f"Error processing query: {str(e)}",
                       operation="query", request_id=request_id, status="error")
        raise HTTPException(status_code=500, detail="Internal server error")

# ---------------------------------------------------------------------------
# Flags / Reviews (Phase 6 + Phase 7 Authorization)
# ---------------------------------------------------------------------------

@app.post("/flags", response_model=FlagRecord)
def flag_knowledge(request: FlagRequest, http_request: Request):
    # Require authentication — fail-closed
    auth_ctx = get_required_auth_context(http_request)
    if auth_ctx and auth_ctx.user_id:
        request.flagged_by = auth_ctx.user_id
    try:
        return review_service.create_flag(request)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating flag: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/reviews", response_model=List[FlagRecord])
def list_reviews(http_request: Request, status: Optional[str] = None):
    # Require authentication — fail-closed
    auth_ctx = get_required_auth_context(http_request)

    # Public users cannot view or audit review queues
    if auth_ctx.role == "public" or auth_ctx.role not in ("team", "developer", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view reviews")

    try:
        return review_service.list_flags(status=status)
    except Exception as e:
        logger.error(f"Error listing reviews: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/reviews/{flag_id}/resolve", response_model=FlagRecord)
def resolve_review(flag_id: str, request: ResolveFlagRequest, http_request: Request):
    # Require authentication — fail-closed
    auth_ctx = get_required_auth_context(http_request)

    # Only authorized reviewers (team/developer/admin) can resolve flags
    if auth_ctx.role not in ("developer", "admin", "team"):
        raise HTTPException(status_code=403, detail="Insufficient permissions to resolve reviews")

    if auth_ctx and auth_ctx.user_id:
        request.reviewer = auth_ctx.user_id

    try:
        return review_service.resolve_flag(flag_id, request)
    except ValidationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error resolving flag {flag_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ---------------------------------------------------------------------------
# Phase 7: Freshness + Conflict endpoints
# ---------------------------------------------------------------------------

@app.get("/documents/{document_id}/freshness")
def get_document_freshness(document_id: str, http_request: Request):
    """
    Returns freshness metadata for a specific document.
    """
    # Require authentication — fail-closed
    auth_ctx = get_required_auth_context(http_request)

    from backend.app.services.dynamodb_service import DynamoDBService
    try:
        doc = DynamoDBService().get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        doc_level = doc.access_level.value if hasattr(doc.access_level, "value") else str(doc.access_level)
        if not auth_service.is_document_authorized(auth_ctx, doc_level):
            raise HTTPException(status_code=403, detail="Access denied to this document")

        # Determine freshness label
        if not doc.is_current:
            freshness_label = "SUPERSEDED"
        elif doc.status.value in ("archived",):
            freshness_label = "ARCHIVED"
        elif doc.status.value in ("pending_review",):
            freshness_label = "PENDING_REVIEW"
        elif doc.indexing_status == "INDEXED":
            freshness_label = "CURRENT"
        else:
            freshness_label = doc.status.value.upper()

        return {
            "document_id": doc.document_id,
            "filename": doc.filename,
            "status": doc.status.value,
            "freshness": freshness_label,
            "is_current": doc.is_current,
            "version": doc.version,
            "content_hash": doc.content_hash,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
            "indexed_at": doc.indexed_at,
            "superseded_by": doc.superseded_by,
            "indexing_status": doc.indexing_status,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting freshness for {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/conflicts", response_model=List[dict])
def list_conflicts(http_request: Request, document_id: Optional[str] = None):
    """
    List detected conflict records, strictly filtered by user's access level against both documents.
    """
    # Require authentication — fail-closed
    auth_ctx = get_required_auth_context(http_request)

    try:
        svc = ConflictService()
        records = svc.list_conflicts(document_id=document_id)

        # Privacy filter: filter out conflicts where user lacks access to BOTH documents
        from backend.app.services.dynamodb_service import DynamoDBService
        ddb = DynamoDBService()
        doc_cache = {}
        filtered_records = []
        for r in records:
            if r.source_document_id not in doc_cache:
                doc_cache[r.source_document_id] = ddb.get_document(r.source_document_id)
            src_doc = doc_cache[r.source_document_id]

            if r.conflicting_document_id not in doc_cache:
                doc_cache[r.conflicting_document_id] = ddb.get_document(r.conflicting_document_id)
            cnf_doc = doc_cache[r.conflicting_document_id]

            src_ok = auth_service.is_document_authorized(
                auth_ctx, src_doc.access_level.value if hasattr(src_doc.access_level, "value") else str(src_doc.access_level)
            ) if src_doc else False
            cnf_ok = auth_service.is_document_authorized(
                auth_ctx, cnf_doc.access_level.value if hasattr(cnf_doc.access_level, "value") else str(cnf_doc.access_level)
            ) if cnf_doc else False

            if src_ok and cnf_ok:
                filtered_records.append(r)

        return [r.model_dump(mode="json") for r in filtered_records]
    except Exception as e:
        logger.error(f"Error listing conflicts: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/documents/{document_id}/conflicts", response_model=List[dict])
def get_document_conflicts(document_id: str, http_request: Request):
    """
    Returns conflicts involving a specific document, strictly filtered by user's access level.
    """
    # Require authentication — fail-closed
    auth_ctx = get_required_auth_context(http_request)

    try:
        from backend.app.services.dynamodb_service import DynamoDBService
        ddb = DynamoDBService()
        doc = ddb.get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        doc_level = doc.access_level.value if hasattr(doc.access_level, "value") else str(doc.access_level)
        if not auth_service.is_document_authorized(auth_ctx, doc_level):
            raise HTTPException(status_code=403, detail="Access denied to document conflicts")

        svc = ConflictService()
        records = svc.list_conflicts(document_id=document_id)

        # Ensure that even for this document, any opposing conflict doc must also be authorized
        doc_cache = {document_id: doc}
        filtered_records = []
        for r in records:
            other_id = r.conflicting_document_id if r.source_document_id == document_id else r.source_document_id
            if other_id not in doc_cache:
                doc_cache[other_id] = ddb.get_document(other_id)
            other_doc = doc_cache[other_id]
            other_ok = auth_service.is_document_authorized(
                auth_ctx, other_doc.access_level.value if hasattr(other_doc.access_level, "value") else str(other_doc.access_level)
            ) if other_doc else False

            if other_ok:
                filtered_records.append(r)

        return [r.model_dump(mode="json") for r in filtered_records]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conflicts for {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
