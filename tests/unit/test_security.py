"""
Phase 7 Tests — Security

Tests 28-30 covering:
28. Unauthorized chunk (wrong access level) never reaches generation model
29. Missing access level on chunk is denied (fail-closed, not fail-open)
30. FAILED document chunk cannot be used as evidence even with valid access level
"""
import pytest
from unittest.mock import patch, MagicMock

from shared.models.query import QueryRequest
from backend.app.services.query_service import QueryService
from shared.constants.document_status import DocumentStatus


@pytest.fixture
def query_service():
    with patch("backend.app.services.query_service.EmbeddingService"), \
         patch("backend.app.services.query_service.OpenSearchService"), \
         patch("backend.app.services.query_service.GenerationService"), \
         patch("backend.app.services.query_service.DynamoDBService"), \
         patch("backend.app.services.query_service.MetricsService"):
        svc = QueryService()
        svc.embedding_service.embed_text.return_value = [0.1] * 1536
        # Default: document is READY + current
        default_doc = MagicMock()
        default_doc.status = DocumentStatus.READY
        default_doc.is_current = True
        svc.dynamodb_service.get_document.return_value = default_doc
        yield svc


# Test 28: Unauthorized chunk (wrong access level) never reaches generation
def test_unauthorized_chunk_never_reaches_generation(query_service):
    """
    A 'developer'-level chunk must not reach generation when user is 'public'.
    """
    request = QueryRequest(question="What is the internal API key?")
    query_service.opensearch_service.search_similar_chunks.return_value = [
        {
            "chunk_id": "secret-chunk", "document_id": "dev-doc",
            "text": "The API key is XYZ123",
            "_score": 0.95, "document_status": "READY",
            "access_level": "developer"  # User only has "public"
        }
    ]

    # User is only cleared for "public"
    response = query_service.query(request)

    # Generation must not have been called
    query_service.generation_service.generate_grounded_answer.assert_not_called()
    assert response.grounded is False
    assert len(response.sources) == 0


# Test 29: Missing access level on chunk is denied (fail-closed)
def test_chunk_missing_access_level_is_denied(query_service):
    """
    A chunk with no access_level field must be denied, not granted.
    This ensures fail-closed behavior for malformed index entries.
    """
    request = QueryRequest(question="Some question?")
    query_service.opensearch_service.search_similar_chunks.return_value = [
        {
            "chunk_id": "no-level-chunk", "document_id": "some-doc",
            "text": "Some content here",
            "_score": 0.9, "document_status": "READY",
            # No "access_level" field at all
        }
    ]

    response = query_service.query(request)

    query_service.generation_service.generate_grounded_answer.assert_not_called()
    assert response.grounded is False
    assert len(response.sources) == 0


# Test 30: FAILED document chunk cannot be evidence even with valid access level
def test_failed_document_cannot_be_evidence(query_service):
    """
    A chunk from a FAILED document must be excluded regardless of access level.
    """
    request = QueryRequest(question="Tell me about X?")
    query_service.opensearch_service.search_similar_chunks.return_value = [
        {
            "chunk_id": "failed-chunk", "document_id": "failed-doc",
            "text": "This content came from a failed document",
            "_score": 0.9, "document_status": "FAILED",  # Index says FAILED
            "access_level": "public"  # User has public access
        }
    ]

    response = query_service.query(request)

    query_service.generation_service.generate_grounded_answer.assert_not_called()
    assert response.grounded is False
    assert len(response.sources) == 0
