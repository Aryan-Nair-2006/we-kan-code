import uuid
from datetime import datetime, timezone
from typing import List, Optional
from shared.models.document import DocumentMetadata
from shared.constants.document_status import DocumentStatus
from shared.constants.access_level import AccessLevel
from backend.app.services.s3_service import S3Service
from backend.app.services.dynamodb_service import DynamoDBService
from backend.app.core.exceptions import ValidationError

class DocumentService:
    def __init__(self):
        self.s3_service = S3Service()
        self.dynamodb_service = DynamoDBService()
        self.supported_types = {"pdf", "docx", "txt"}
        
    def upload_document(self, file_bytes: bytes, filename: str, owner: str, category: str, access_level: AccessLevel, version: str) -> DocumentMetadata:
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext not in self.supported_types:
            raise ValidationError(f"Unsupported file type. Supported types: {', '.join(self.supported_types)}")
            
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
            s3_key=None
        )
        
        # Save to S3
        s3_key = f"documents/raw/{doc_id}/{filename}"
        s3_metadata = {
            "document_id": str(doc_id),
            "owner": str(owner),
            "category": str(category),
            "access_level": str(access_level.value),
            "version": str(version),
            "original_filename": str(filename)
        }
        self.s3_service.upload_file(file_bytes, s3_key, metadata=s3_metadata)
        metadata.s3_key = s3_key
        
        # Save to DynamoDB
        return self.dynamodb_service.create_document(metadata)
        
    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        return self.dynamodb_service.get_document(document_id)
        
    def list_documents(self) -> List[DocumentMetadata]:
        return self.dynamodb_service.list_documents()
