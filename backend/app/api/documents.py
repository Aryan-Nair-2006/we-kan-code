from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from typing import List
from pydantic import ValidationError as PydanticValidationError
from backend.app.services.document_service import DocumentService
from backend.app.services.authorization_service import AuthorizationService, get_required_auth_context
from shared.constants.access_level import AccessLevel
from shared.models.document import DocumentMetadata
from backend.app.core.exceptions import ValidationError, StorageError
from backend.app.core.config import settings
from backend.app.core.logging import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])
doc_service = DocumentService()
auth_service = AuthorizationService()

@router.post("/upload", response_model=DocumentMetadata)
async def upload_document(
    http_request: Request,
    file: UploadFile = File(...),
    owner: str = Form(...),
    category: str = Form(...),
    access_level: AccessLevel = Form(...),
    version: str = Form(...)
):
    # 1. Require authentication — fail-closed
    auth_ctx = get_required_auth_context(http_request)

    # 2. Public users are forbidden from uploading documents
    if auth_ctx.role == "public" or auth_ctx.role not in ("team", "developer", "admin"):
        raise HTTPException(status_code=403, detail="Public users are not authorized to upload documents")

    # 3. User cannot upload document higher than their own clearance
    req_level = access_level.value if hasattr(access_level, "value") else str(access_level)
    if not auth_service.is_document_authorized(auth_ctx, req_level):
        raise HTTPException(status_code=403, detail=f"Insufficient permissions to upload document with {req_level} access level")

    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="File is empty")
            
        size_mb = len(file_bytes) / (1024 * 1024)
        if size_mb > settings.max_upload_size_mb:
            raise HTTPException(status_code=400, detail=f"File exceeds maximum allowed size of {settings.max_upload_size_mb}MB")
            
        return doc_service.upload_document(
            file_bytes=file_bytes,
            filename=file.filename or "unknown",
            owner=owner,
            category=category,
            access_level=access_level,
            version=version
        )
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"Validation error during upload: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except StorageError as e:
        logger.error(f"Storage error during upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to store document")
    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("", response_model=List[DocumentMetadata])
def list_documents(http_request: Request):
    # 1. Require authentication — fail-closed
    auth_ctx = get_required_auth_context(http_request)

    all_docs = doc_service.list_documents()
    return [
        doc for doc in all_docs
        if auth_service.is_document_authorized(
            auth_ctx,
            doc.access_level.value if hasattr(doc.access_level, "value") else str(doc.access_level)
        )
    ]

@router.get("/{document_id}", response_model=DocumentMetadata)
def get_document(document_id: str, http_request: Request):
    # 1. Require authentication — fail-closed
    auth_ctx = get_required_auth_context(http_request)

    doc = doc_service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_level = doc.access_level.value if hasattr(doc.access_level, "value") else str(doc.access_level)
    if not auth_service.is_document_authorized(auth_ctx, doc_level):
        raise HTTPException(status_code=403, detail="Access denied to this document")

    return doc
