from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List
from pydantic import ValidationError as PydanticValidationError
from backend.app.services.document_service import DocumentService
from shared.constants.access_level import AccessLevel
from shared.models.document import DocumentMetadata
from backend.app.core.exceptions import ValidationError, StorageError
from backend.app.core.config import settings
from backend.app.core.logging import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])
doc_service = DocumentService()

@router.post("/upload", response_model=DocumentMetadata)
async def upload_document(
    file: UploadFile = File(...),
    owner: str = Form(...),
    category: str = Form(...),
    access_level: AccessLevel = Form(...),
    version: str = Form(...)
):
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
def list_documents():
    return doc_service.list_documents()

@router.get("/{document_id}", response_model=DocumentMetadata)
def get_document(document_id: str):
    doc = doc_service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
