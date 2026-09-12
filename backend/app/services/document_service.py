import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from shared.models.document import DocumentMetadata
from shared.constants.document_status import DocumentStatus
from shared.constants.access_level import AccessLevel
from backend.app.services.s3_service import S3Service
from backend.app.services.dynamodb_service import DynamoDBService
from backend.app.core.exceptions import ValidationError
from backend.app.core.logging import setup_logger

logger = setup_logger(__name__)

class DocumentService:
    def __init__(self):
        self.s3_service = S3Service()
        self.dynamodb_service = DynamoDBService()
        self.supported_types = {"pdf", "docx", "txt", "xlsx", "csv", "pptx", "md"}
        
    def upload_document(
        self,
        file_bytes: bytes,
        filename: str,
        owner: str,
        category: str,
        access_level: AccessLevel,
        version: str
    ) -> DocumentMetadata:
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext not in self.supported_types:
            raise ValidationError(
                f"Unsupported file type. Supported types: {', '.join(self.supported_types)}"
            )

        # Phase 7: Compute content hash for duplicate/version detection
        content_hash = hashlib.sha256(file_bytes).hexdigest()

        # Phase 7: Check for an existing document with the same logical identity
        # (same filename + owner + category) to determine if this is a new version
        existing_current = self._find_current_document(filename, owner, category)

        if existing_current is not None:
            if existing_current.content_hash == content_hash:
                # Exact same bytes — deduplicate, no re-index needed
                logger.info(
                    f"Duplicate upload detected for '{filename}' (hash matches). "
                    f"Returning existing document {existing_current.document_id}."
                )
                return existing_current

            # Different content — this is a new version; supersede the old one
            logger.info(
                f"New version of '{filename}' detected. "
                f"Superseding document {existing_current.document_id}."
            )
            # We'll back-patch superseded_by after we know the new doc ID

        doc_id = f"DOC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
        now_str = datetime.now(timezone.utc).isoformat()

        metadata = DocumentMetadata(
            document_id=doc_id,
            filename=filename,
            file_type=ext,
            owner=owner,
            category=category,
            access_level=access_level,
            version=version,
            created_at=now_str,
            updated_at=now_str,
            status=DocumentStatus.UPLOADED,
            s3_key=None,
            content_hash=content_hash,
            is_current=True,
        )

        # Supersede the old document now that we have the new doc_id
        if existing_current is not None:
            existing_current.status = DocumentStatus.SUPERSEDED
            existing_current.is_current = False
            existing_current.superseded_by = doc_id
            existing_current.updated_at = now_str
            self.dynamodb_service.update_document(existing_current)
            logger.info(f"Marked document {existing_current.document_id} as SUPERSEDED by {doc_id}")

        # Save to S3
        s3_key = f"documents/raw/{doc_id}/{filename}"
        s3_metadata = {
            "document_id": str(doc_id),
            "owner": str(owner),
            "category": str(category),
            "access_level": str(access_level.value),
            "version": str(version),
            "original_filename": str(filename),
            "content_hash": content_hash,
        }
        self.s3_service.upload_file(file_bytes, s3_key, metadata=s3_metadata)
        metadata.s3_key = s3_key

        # Save to DynamoDB
        return self.dynamodb_service.create_document(metadata)

    def _find_current_document(
        self, filename: str, owner: str, category: str
    ) -> Optional[DocumentMetadata]:
        """
        Find the current (is_current=True) document with the given logical identity.
        Logical identity = filename + owner + category.
        Returns None if no matching current document exists.
        """
        try:
            all_docs = self.dynamodb_service.list_documents()
            for doc in all_docs:
                if (
                    doc.filename == filename
                    and doc.owner == owner
                    and doc.category == category
                    and doc.is_current
                    and doc.status not in (DocumentStatus.SUPERSEDED, DocumentStatus.ARCHIVED)
                ):
                    return doc
        except Exception as e:
            logger.warning(f"Could not check for existing document version: {e}")
        return None

    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        return self.dynamodb_service.get_document(document_id)
        
    def list_documents(self) -> List[DocumentMetadata]:
        return self.dynamodb_service.list_documents()
