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

_LOCAL_FLAGS_STORE: dict[str, FlagRecord] = {}


class ReviewService:
    def __init__(self, table_name: str = settings.reviews_table_name):
        self.table_name = table_name
        self.table = None
        if boto3.Session().get_credentials() is not None:
            try:
                self.dynamodb = boto3.resource('dynamodb', region_name=settings.aws_region)
                self.table = self.dynamodb.Table(self.table_name)
            except Exception as e:
                logger.warning(f"Review table init warning: {e}")
                self.table = None
        self.documents = DynamoDBService()

    def create_flag(self, request: FlagRequest) -> FlagRecord:
        doc = self.documents.get_document(request.document_id) if request.document_id != "DOC-UNKNOWN" else None
        if not doc and request.document_id != "DOC-UNKNOWN":
            raise ValidationError(f"Document {request.document_id} not found")

        record = FlagRecord(
            flag_id=str(uuid.uuid4()),
            document_id=request.document_id,
            chunk_id=request.chunk_id,
            reason=request.reason,
            details=request.details,
            question=request.question,
            answer=request.answer,
            source_filename=request.source_filename or (doc.filename if doc else "Unknown"),
            supporting_passage=request.supporting_passage,
            flagged_by=request.flagged_by,
            status="OPEN",
            created_at=_now_iso(),
        )
        _LOCAL_FLAGS_STORE[record.flag_id] = record
        if self.table:
            try:
                self.table.put_item(Item=record.model_dump(mode='json'))
            except Exception as e:
                logger.warning(f"Failed to create flag in DynamoDB: {str(e)}")

        if doc:
            doc.status = DocumentStatus.PENDING_REVIEW
            self.documents.update_document(doc)

        return record

    def list_flags(self, status: Optional[str] = None) -> List[FlagRecord]:
        if self.table:
            try:
                response = self.table.scan()
                items = response.get('Items', [])
                for item in items:
                    f = FlagRecord(**item)
                    _LOCAL_FLAGS_STORE[f.flag_id] = f
            except Exception as e:
                logger.warning(f"DynamoDB scan error (using local store): {str(e)}")

        records = list(_LOCAL_FLAGS_STORE.values())
        if status:
            records = [r for r in records if r.status.upper() == status.upper()]
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records

    def get_flag(self, flag_id: str) -> Optional[FlagRecord]:
        if self.table:
            try:
                response = self.table.get_item(Key={'flag_id': flag_id})
                item = response.get('Item')
                if item:
                    return FlagRecord(**item)
            except Exception as e:
                logger.warning(f"DynamoDB get flag error (using local store): {str(e)}")

        return _LOCAL_FLAGS_STORE.get(flag_id)

    def resolve_flag(self, flag_id: str, resolution: ResolveFlagRequest) -> FlagRecord:
        record = self.get_flag(flag_id)
        if not record:
            raise ValidationError(f"Flag {flag_id} not found")

        valid_actions = {"CORRECTED", "DISMISSED", "ARCHIVE_DOCUMENT", "RESOLVED"}
        res_action = resolution.resolution.upper()
        if res_action not in valid_actions:
            raise ValidationError(f"Invalid resolution action: {resolution.resolution}. Must be one of {sorted(list(valid_actions))}")

        status_value = "DISMISSED" if res_action == "DISMISSED" else "RESOLVED"
        record.status = status_value
        record.resolved_at = _now_iso()
        record.resolution = res_action
        record.reviewer = resolution.reviewer
        record.notes = resolution.notes

        _LOCAL_FLAGS_STORE[record.flag_id] = record

        if self.table:
            try:
                self.table.put_item(Item=record.model_dump(mode='json'))
            except Exception as e:
                logger.warning(f"DynamoDB put flag resolution warning: {str(e)}")

        if record.document_id and record.document_id != "DOC-UNKNOWN":
            doc = self.documents.get_document(record.document_id)
            if doc:
                remaining_open = [f for f in self.list_flags(status="OPEN") if f.document_id == doc.document_id]
                if res_action == "ARCHIVE_DOCUMENT":
                    doc.status = DocumentStatus.ARCHIVED
                elif not remaining_open:
                    doc.status = DocumentStatus.READY
                self.documents.update_document(doc)

        return record
