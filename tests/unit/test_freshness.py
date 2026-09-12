"""
Phase 7 Tests — Freshness / Versioning

Tests 8-14 covering:
8. Current document is queryable
9. Superseded document is rejected
10. Archived document is rejected
11. Pending-review document is rejected
12. Stale OpenSearch vector is rejected using DynamoDB metadata
13. Unchanged duplicate upload does not create unnecessary version
14. Changed content creates a new version and marks old SUPERSEDED
"""
import hashlib
import pytest
from unittest.mock import patch, MagicMock, call
from shared.models.query import QueryRequest, SourceCitation
from shared.models.document import DocumentMetadata
from shared.constants.document_status import DocumentStatus
from shared.constants.access_level import AccessLevel
from backend.app.services.query_service import QueryService


@pytest.fixture
def query_service():
    with patch("backend.app.services.query_service.EmbeddingService"), \
         patch("backend.app.services.query_service.OpenSearchService"), \
         patch("backend.app.services.query_service.GenerationService"), \
         patch("backend.app.services.query_service.DynamoDBService"), \
         patch("backend.app.services.query_service.MetricsService"):
        svc = QueryService()
        svc.embedding_service.embed_text.return_value = [0.1] * 1536
        yield svc


def make_source(doc_id="d1", chunk_id="c1", access_level="public"):
    return SourceCitation(
        chunk_id=chunk_id, document_id=doc_id, text="Some text",
        access_level=access_level, similarity=0.9
    )


def make_doc(doc_id="d1", status=DocumentStatus.READY, is_current=True, superseded_by=None):
    return DocumentMetadata(
        document_id=doc_id, filename="test.pdf", file_type="pdf",
        owner="owner", category="cat", created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z", version="1.0",
        access_level=AccessLevel.PUBLIC, status=status,
        is_current=is_current, superseded_by=superseded_by
    )


# Test 8: Current document is queryable
def test_current_document_is_queryable(query_service):
    doc = make_doc(status=DocumentStatus.READY, is_current=True)
    query_service.dynamodb_service.get_document.return_value = doc
    sources = [make_source()]
    result = query_service._filter_by_live_status(sources)
    assert len(result) == 1


# Test 9: Superseded document is rejected
def test_superseded_document_is_rejected(query_service):
    doc = make_doc(status=DocumentStatus.SUPERSEDED, is_current=False, superseded_by="d2")
    query_service.dynamodb_service.get_document.return_value = doc
    sources = [make_source()]
    result = query_service._filter_by_live_status(sources)
    assert len(result) == 0


# Test 10: Archived document is rejected
def test_archived_document_is_rejected(query_service):
    doc = make_doc(status=DocumentStatus.ARCHIVED)
    query_service.dynamodb_service.get_document.return_value = doc
    sources = [make_source()]
    result = query_service._filter_by_live_status(sources)
    assert len(result) == 0


# Test 11: Pending-review document is rejected
def test_pending_review_document_is_rejected(query_service):
    doc = make_doc(status=DocumentStatus.PENDING_REVIEW)
    query_service.dynamodb_service.get_document.return_value = doc
    sources = [make_source()]
    result = query_service._filter_by_live_status(sources)
    assert len(result) == 0


# Test 12: Stale OpenSearch vector is rejected using live DynamoDB status
def test_stale_opensearch_vector_rejected_via_dynamodb(query_service):
    """
    OpenSearch chunk claims document_status=READY (snapshot from index time),
    but DynamoDB live check says PENDING_REVIEW. The chunk must be excluded.
    """
    request = QueryRequest(question="What is X?")
    query_service.opensearch_service.search_similar_chunks.return_value = [
        {
            "chunk_id": "c1", "document_id": "d1", "text": "Some text",
            "_score": 0.9, "document_status": "READY", "access_level": "public"
        }
    ]
    # Live DynamoDB says it's under review since indexing
    flagged_doc = make_doc(status=DocumentStatus.PENDING_REVIEW)
    query_service.dynamodb_service.get_document.return_value = flagged_doc

    response = query_service.query(request)
    assert response.grounded is False
    assert len(response.sources) == 0
    query_service.generation_service.generate_grounded_answer.assert_not_called()


# Test 13: Unchanged duplicate upload does not create a new version
def test_duplicate_upload_no_new_version():
    file_bytes = b"identical document content"
    content_hash = hashlib.sha256(file_bytes).hexdigest()

    existing_doc = make_doc()
    existing_doc.content_hash = content_hash
    existing_doc.filename = "report.pdf"
    existing_doc.owner = "alice"
    existing_doc.category = "engineering"

    with patch("backend.app.services.document_service.S3Service"), \
         patch("backend.app.services.document_service.DynamoDBService") as mock_ddb:
        from backend.app.services.document_service import DocumentService
        svc = DocumentService()
        # list_documents returns the existing doc with same hash
        svc.dynamodb_service.list_documents.return_value = [existing_doc]

        result = svc.upload_document(
            file_bytes=file_bytes,
            filename="report.pdf",
            owner="alice",
            category="engineering",
            access_level=AccessLevel.PUBLIC,
            version="1.0"
        )

    # Should return the existing document without creating a new one
    assert result.document_id == existing_doc.document_id
    # update_document should NOT have been called to mark it superseded
    svc.dynamodb_service.create_document.assert_not_called()


# Test 14: Changed content creates a new version and marks old SUPERSEDED
def test_changed_content_creates_new_version_and_supersedes_old():
    old_bytes = b"version 1 content"
    new_bytes = b"version 2 content - different"

    old_hash = hashlib.sha256(old_bytes).hexdigest()

    existing_doc = MagicMock(spec=DocumentMetadata)
    existing_doc.document_id = "DOC-OLD"
    existing_doc.filename = "spec.pdf"
    existing_doc.owner = "bob"
    existing_doc.category = "specs"
    existing_doc.content_hash = old_hash
    existing_doc.is_current = True
    existing_doc.status = DocumentStatus.READY

    with patch("backend.app.services.document_service.S3Service"), \
         patch("backend.app.services.document_service.DynamoDBService"):
        from backend.app.services.document_service import DocumentService
        svc = DocumentService()
        svc.dynamodb_service.list_documents.return_value = [existing_doc]

        new_meta = MagicMock()
        new_meta.document_id = "DOC-NEW"
        svc.dynamodb_service.create_document.return_value = new_meta

        result = svc.upload_document(
            file_bytes=new_bytes,
            filename="spec.pdf",
            owner="bob",
            category="specs",
            access_level=AccessLevel.PUBLIC,
            version="2.0"
        )

    # Old doc must be marked SUPERSEDED
    assert existing_doc.status == DocumentStatus.SUPERSEDED
    assert existing_doc.is_current is False
    assert existing_doc.superseded_by is not None

    # A new document must be created
    svc.dynamodb_service.create_document.assert_called_once()

    # The new doc should also be uploaded to S3
    svc.s3_service.upload_file.assert_called_once()
