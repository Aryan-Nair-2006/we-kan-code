"""
Phase 7 Tests — Conflict Detection

Tests 15-19 covering:
15. Conflicting candidate pair creates conflict record
16. Unrelated documents do not create conflicts
17. Malformed Bedrock classifier response does not create false conflict
18. Resolved conflict is represented correctly in model
19. Known conflict causes warning/abstention behavior in query pipeline
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from backend.app.services.conflict_service import ConflictService


@pytest.fixture
def conflict_service():
    with patch("backend.app.services.conflict_service.boto3"):
        svc = ConflictService()
        svc.enabled = True
        svc.threshold = 0.75
        svc.max_candidates = 3
        svc._bedrock = MagicMock()
        svc._dynamodb = MagicMock()
        return svc


def _mock_bedrock_response(relationship: str, confidence: float, reason: str = "test"):
    """Helper to produce a Bedrock-style response."""
    output = json.dumps({
        "relationship": relationship,
        "confidence": confidence,
        "reason": reason
    })
    body_mock = MagicMock()
    body_mock.read.return_value = json.dumps({
        "results": [{"outputText": output}]
    }).encode()
    return {"body": body_mock}


# Test 15: Conflicting candidate pair creates conflict record
def test_conflicting_pair_creates_conflict_record(conflict_service):
    # Mock OpenSearch returning a similar chunk from a different document
    mock_opensearch = MagicMock()
    mock_opensearch.search_similar_chunks.return_value = [
        {
            "chunk_id": "other-chunk-1", "document_id": "other-doc",
            "text": "The timeout is 60 seconds.", "_score": 0.85,
            "document_status": "READY"
        }
    ]

    # Mock Bedrock returning CONTRADICTS
    conflict_service.bedrock.invoke_model.return_value = _mock_bedrock_response(
        "CONTRADICTS", 0.91, "Different timeout values specified"
    )

    mock_embedding = MagicMock()
    mock_embedding.embed_text.return_value = [0.1] * 1536

    chunks = [{"chunk_id": "chunk-1", "text": "The timeout is 30 seconds."}]

    # store_conflict calls dynamodb_table.put_item
    conflict_service.dynamodb_table.put_item = MagicMock()

    count = conflict_service.detect_conflicts(
        document_id="source-doc",
        chunks=chunks,
        opensearch_service=mock_opensearch,
        embedding_service=mock_embedding,
    )

    assert count == 1
    conflict_service.dynamodb_table.put_item.assert_called_once()


# Test 16: Unrelated documents do not create conflicts
def test_unrelated_documents_no_conflict(conflict_service):
    mock_opensearch = MagicMock()
    mock_opensearch.search_similar_chunks.return_value = [
        {
            "chunk_id": "other-chunk-2", "document_id": "other-doc",
            "text": "The sky is blue.", "_score": 0.75,
            "document_status": "READY"
        }
    ]

    # Bedrock says UNRELATED
    conflict_service.bedrock.invoke_model.return_value = _mock_bedrock_response(
        "UNRELATED", 0.95
    )

    mock_embedding = MagicMock()
    mock_embedding.embed_text.return_value = [0.1] * 1536

    chunks = [{"chunk_id": "chunk-2", "text": "The API uses REST architecture."}]
    conflict_service.dynamodb_table.put_item = MagicMock()

    count = conflict_service.detect_conflicts(
        document_id="source-doc",
        chunks=chunks,
        opensearch_service=mock_opensearch,
        embedding_service=mock_embedding,
    )

    assert count == 0
    conflict_service.dynamodb_table.put_item.assert_not_called()


# Test 17: Malformed Bedrock classifier response does not create false conflict
def test_malformed_bedrock_response_no_false_conflict(conflict_service):
    mock_opensearch = MagicMock()
    mock_opensearch.search_similar_chunks.return_value = [
        {
            "chunk_id": "other-chunk-3", "document_id": "other-doc",
            "text": "Some text.", "_score": 0.8,
            "document_status": "READY"
        }
    ]

    # Bedrock returns garbage
    body_mock = MagicMock()
    body_mock.read.return_value = json.dumps({
        "results": [{"outputText": "NOT JSON AT ALL !!!"}]
    }).encode()
    conflict_service.bedrock.invoke_model.return_value = {"body": body_mock}

    mock_embedding = MagicMock()
    mock_embedding.embed_text.return_value = [0.1] * 1536

    chunks = [{"chunk_id": "chunk-3", "text": "Some content here."}]
    conflict_service.dynamodb_table.put_item = MagicMock()

    # Should not raise and should not create any conflict
    count = conflict_service.detect_conflicts(
        document_id="source-doc",
        chunks=chunks,
        opensearch_service=mock_opensearch,
        embedding_service=mock_embedding,
    )

    assert count == 0
    conflict_service.dynamodb_table.put_item.assert_not_called()


# Test 18: parse_classifier_response validates fields correctly
def test_parse_classifier_response_validates_fields():
    # Valid response
    result = ConflictService._parse_classifier_response(
        '{"relationship": "CONTRADICTS", "confidence": 0.85, "reason": "different values"}'
    )
    assert result is not None
    assert result["relationship"] == "CONTRADICTS"
    assert result["confidence"] == 0.85

    # Invalid relationship
    result = ConflictService._parse_classifier_response(
        '{"relationship": "MAYBE", "confidence": 0.85, "reason": "test"}'
    )
    assert result is None

    # Confidence out of range
    result = ConflictService._parse_classifier_response(
        '{"relationship": "CONTRADICTS", "confidence": 1.5, "reason": "test"}'
    )
    assert result is None

    # Empty input
    result = ConflictService._parse_classifier_response("")
    assert result is None

    # Missing confidence
    result = ConflictService._parse_classifier_response(
        '{"relationship": "CONTRADICTS", "reason": "test"}'
    )
    assert result is None


# Test 19: Known conflict causes warning in query pipeline
def test_known_conflict_causes_warning_in_query():
    from unittest.mock import patch, MagicMock
    from shared.models.query import QueryRequest
    from shared.models.document import ConflictRecord
    from shared.constants.document_status import DocumentStatus
    from backend.app.services.query_service import QueryService
    from datetime import datetime, timezone

    request = QueryRequest(question="What is the timeout?")

    conflict = ConflictRecord(
        conflict_id="c-1",
        source_document_id="doc-a",
        source_chunk_id="chunk-a",
        conflicting_document_id="doc-b",
        conflicting_chunk_id="chunk-b",
        relationship="CONTRADICTS",
        confidence=0.91,
        topic="Different timeout values",
        detected_at=datetime.now(timezone.utc).isoformat(),
        status="OPEN"
    )

    with patch("backend.app.services.query_service.EmbeddingService"), \
         patch("backend.app.services.query_service.OpenSearchService"), \
         patch("backend.app.services.query_service.GenerationService"), \
         patch("backend.app.services.query_service.DynamoDBService"), \
         patch("backend.app.services.query_service.MetricsService"), \
         patch("backend.app.services.conflict_service.ConflictService") as mock_cs:
        svc = QueryService()
        svc.embedding_service.embed_text.return_value = [0.1] * 1536

        # Both docs are READY + current
        ready_doc_a = MagicMock()
        ready_doc_a.status = DocumentStatus.READY
        ready_doc_a.is_current = True

        ready_doc_b = MagicMock()
        ready_doc_b.status = DocumentStatus.READY
        ready_doc_b.is_current = True

        def get_doc(doc_id):
            return ready_doc_a if doc_id == "doc-a" else ready_doc_b

        svc.dynamodb_service.get_document.side_effect = get_doc

        svc.opensearch_service.search_similar_chunks.return_value = [
            {"chunk_id": "chunk-a", "document_id": "doc-a", "text": "Timeout is 30s",
             "_score": 0.9, "document_status": "READY", "access_level": "public"},
            {"chunk_id": "chunk-b", "document_id": "doc-b", "text": "Timeout is 60s",
             "_score": 0.85, "document_status": "READY", "access_level": "public"},
        ]
        svc.generation_service.generate_grounded_answer.return_value = "Answer [S1] and [S2]"

        # Mock conflict service returning the conflict
        mock_cs_instance = MagicMock()
        mock_cs_instance.get_conflicts_for_document_ids.return_value = [conflict]
        mock_cs.return_value = mock_cs_instance

        response = svc.query(request)

    assert response.conflict_warning is True
    assert response.conflict_details is not None
    assert "doc-a" in response.conflict_details or "doc-b" in response.conflict_details
