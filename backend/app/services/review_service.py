import uuid
from datetime import datetime, timezone
from typing import List, Optional

import boto3

from backend.app.core.config import settings
from backend.app.core.exceptions import StorageError, ValidationError
from backend.app.core.logging import setup_logger
from backend.app.services.dynamodb_service import DynamoDBService
from shared.constants.document_status import DocumentStatus
from shared.models.document import FlagRecord, FlagRequest, ResolveFlagRequest

logger = setup_logger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReviewService:
    """
    Owns the freshness/review workflow: recording flags against documents or
    chunks, listing them for reviewers, and resolving them. Deliberately kept
    simple for a hackathon build:
      - "CORRECTED" unblocks the document (sets it back to READY) but does NOT
        re-run ingestion/indexing automatically. The document owner still needs
        to re-upload the corrected file for the new content to actually reach
        the index. Flagged here so nobody assumes this is fully automatic.
      - "ARCHIVE_DOCUMENT" marks the document ARCHIVED so new queries stop
        surfacing it, but does not retroactively purge chunks already indexed
        in OpenSearch. A full removal would need an explicit delete-by-query
        against the index, left out to fit the time budget.
    """

    def __init__(self, table_name: str = settings.reviews_table_name):
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', region_name=settings.aws_region)
        self.table = self.dynamodb.Table(self.table_name)
        self.documents = DynamoDBService()

    def create_flag(self, request: FlagRequest) -> FlagRecord:
        doc = self.documents.get_document(request.document_id)
        if not doc:
            raise ValidationError(f"Document {request.document_id} not found")

        record = FlagRecord(
            flag_id=str(uuid.uuid4()),
            document_id=request.document_id,
            chunk_id=request.chunk_id,
            reason=request.reason,
            flagged_by=request.flagged_by,
            status="OPEN",
            created_at=_now_iso(),
        )
        try:
            self.table.put_item(Item=record.model_dump(mode='json'))
        except Exception as e:
            logger.error(f"Failed to create flag: {str(e)}")
            raise StorageError(f"DynamoDB error: {str(e)}")

        # Surface the flag on the document itself so it's visible outside the
        # review page too (badge in the library/home views).
        doc.status = DocumentStatus.PENDING_REVIEW
        self.documents.update_document(doc)

        return record

    def list_flags(self, status: Optional[str] = None) -> List[FlagRecord]:
        try:
            response = self.table.scan()
            items = response.get('Items', [])
        except Exception as e:
            logger.error(f"Failed to list flags: {str(e)}")
            raise StorageError(f"DynamoDB scan error: {str(e)}")

        records = [FlagRecord(**item) for item in items]
        if status:
            records = [r for r in records if r.status.upper() == status.upper()]
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records

    def get_flag(self, flag_id: str) -> Optional[FlagRecord]:
        try:
            response = self.table.get_item(Key={'flag_id': flag_id})
            item = response.get('Item')
            return FlagRecord(**item) if item else None
        except Exception as e:
            logger.error(f"Failed to get flag {flag_id}: {str(e)}")
            raise StorageError(f"DynamoDB error: {str(e)}")

    def resolve_flag(self, flag_id: str, resolution: ResolveFlagRequest) -> FlagRecord:
        record = self.get_flag(flag_id)
        if not record:
            raise ValidationError(f"Flag {flag_id} not found")

        record.status = "RESOLVED"
        record.resolved_at = _now_iso()
        record.resolution = resolution.resolution
        record.reviewer = resolution.reviewer
        record.notes = resolution.notes

        try:
            self.table.put_item(Item=record.model_dump(mode='json'))
        except Exception as e:
            logger.error(f"Failed to resolve flag {flag_id}: {str(e)}")
            raise StorageError(f"DynamoDB error: {str(e)}")

        doc = self.documents.get_document(record.document_id)
        if doc:
            remaining_open = [f for f in self.list_flags(status="OPEN") if f.document_id == doc.document_id]
            if resolution.resolution == "ARCHIVE_DOCUMENT":
                doc.status = DocumentStatus.ARCHIVED
            elif not remaining_open:
                # No other open flags against this document: safe to unblock it.
                doc.status = DocumentStatus.READY
            self.documents.update_document(doc)

        return record
