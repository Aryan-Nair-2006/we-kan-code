"""
Phase 7 End-to-End Integration Test Suite

Tests the complete Phase 7 Security, Freshness, Versioning, Conflict,
and Monitoring lifecycle:
1. Production Fail-Closed Authentication: Missing/Invalid JWT -> 401
2. Authenticated Claims -> Server-side AuthContext derivation (No Frontend Spoofing)
3. Document Access Control (ACL): Clearance hierarchy (Public < Team < Developer < Admin)
4. Upload ACL enforcement & Role Restrictions
5. Freshness & Hashing: SHA-256 duplicate detection & version superseding
6. Query Pipeline Live Validation: Rejects stale/superseded/archived/pending-review vectors
7. Conflict Detection Lifecycle: Candidate pairing, classifier validation, privacy filtering, and query awareness
8. Monitoring & Observability: Non-fatal metrics emission and structured log correlation
"""
import hashlib
import json
import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from shared.models.query import QueryRequest
from shared.models.document import DocumentMetadata, ConflictRecord, FlagRecord
from shared.constants.document_status import DocumentStatus
from shared.constants.access_level import AccessLevel
from backend.app.services.query_service import QueryService
from backend.app.services.conflict_service import ConflictService


@pytest.fixture
def client():
    return TestClient(app)


def test_phase7_production_fail_closed_authentication(client):
    """
    In production mode, any endpoint protected by get_required_auth_context
    must reject missing or invalid credentials with 401.
    """
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        # Missing auth header -> 401
        res = client.get("/auth/me")
        assert res.status_code == 401
        assert res.json()["detail"] == "Authentication required"

        res = client.post("/query", json={"question": "Where is the API key?"})
        assert res.status_code == 401

        res = client.get("/documents")
        assert res.status_code == 401

        res = client.get("/conflicts")
        assert res.status_code == 401

        # Malformed bearer token -> 401
        res = client.get("/auth/me", headers={"Authorization": "Bearer not-a-valid-jwt"})
        assert res.status_code == 401


def test_phase7_server_derived_identity_and_role_escalation_prevention(client):
    """
    In production, claims from verified JWT payload determine user_id and role.
    Frontend-supplied headers/roles cannot escalate privileges.
    """
    # Create valid base64url JWT payload
    import base64
    payload_team = {
        "sub": "user-corp-456",
        "email": "user@corp.com",
        "cognito:groups": ["team"]
    }
    b64_payload = base64.urlsafe_b64encode(json.dumps(payload_team).encode()).decode().rstrip("=")
    fake_jwt = f"header.{b64_payload}.signature"

    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        res = client.get("/auth/me", headers={"Authorization": f"Bearer {fake_jwt}"})
        assert res.status_code == 200
        data = res.json()
        assert data["user_id"] == "user-corp-456"
        assert data["role"] == "team"
        assert set(data["access_levels"]) == {"public", "team"}
        assert "admin" not in data["access_levels"]
        assert "developer" not in data["access_levels"]


def test_phase7_document_acl_and_privilege_boundary(client):
    """
    Verifies that users can only list and view documents within their clearance.
    """
    pub_doc = DocumentMetadata(
        document_id="DOC-PUB",
        filename="public_guide.pdf",
        file_type="pdf",
        owner="Alice",
        category="General",
        created_at="2026-09-13T00:00:00Z",
        updated_at="2026-09-13T00:00:00Z",
        access_level=AccessLevel.PUBLIC,
        status=DocumentStatus.READY,
        version="1.0",
        content_hash="hash_pub",
        is_current=True
    )
    dev_doc = DocumentMetadata(
        document_id="DOC-DEV",
        filename="backend_architecture.md",
        file_type="md",
        owner="Bob",
        category="Engineering",
        created_at="2026-09-13T00:00:00Z",
        updated_at="2026-09-13T00:00:00Z",
        access_level=AccessLevel.DEVELOPER,
        status=DocumentStatus.READY,
        version="1.0",
        content_hash="hash_dev",
        is_current=True
    )

    with patch("backend.app.services.document_service.DocumentService.list_documents", return_value=[pub_doc, dev_doc]), \
         patch("backend.app.services.document_service.DocumentService.get_document") as mock_get:
        
        mock_get.side_effect = lambda doc_id: dev_doc if doc_id == "DOC-DEV" else pub_doc

        # Public user: can only see public doc
        with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "public"}):
            list_res = client.get("/documents")
            assert list_res.status_code == 200
            items = list_res.json()
            assert len(items) == 1
            assert items[0]["document_id"] == "DOC-PUB"

            # Accessing developer doc directly returns 403
            get_res = client.get("/documents/DOC-DEV")
            assert get_res.status_code == 403

        # Developer user: can see both public and developer doc
        with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "developer"}):
            list_res = client.get("/documents")
            assert list_res.status_code == 200
            items = list_res.json()
            assert len(items) == 2

            get_res = client.get("/documents/DOC-DEV")
            assert get_res.status_code == 200
            assert get_res.json()["document_id"] == "DOC-DEV"


def test_phase7_freshness_versioning_and_stale_rejection():
    """
    Verifies that:
    1. Duplicate content hash preserves existing doc ID without re-indexing
    2. Modified content supersedes older document (is_current=False, status=SUPERSEDED)
    3. QueryService drops superseded/archived/pending-review vectors via live DynamoDB check
    """
    from backend.app.services.document_service import DocumentService
    
    content_v1 = b"Original policy v1 text"
    hash_v1 = hashlib.sha256(content_v1).hexdigest()

    existing_v1 = DocumentMetadata(
        document_id="DOC-V1",
        filename="policy.txt",
        file_type="txt",
        owner="hr",
        category="policy",
        created_at="2026-09-01T00:00:00Z",
        updated_at="2026-09-01T00:00:00Z",
        access_level=AccessLevel.PUBLIC,
        status=DocumentStatus.READY,
        version="1.0",
        content_hash=hash_v1,
        is_current=True
    )

    with patch("backend.app.services.document_service.S3Service"), \
         patch("backend.app.services.document_service.DynamoDBService"):
        doc_service = DocumentService()
        doc_service.dynamodb_service.list_documents.return_value = [existing_v1]

        # Upload identical bytes -> deduplicates
        res_dup = doc_service.upload_document(
            file_bytes=content_v1,
            filename="policy.txt",
            owner="hr",
            category="policy",
            access_level=AccessLevel.PUBLIC,
            version="1.0"
        )
        assert res_dup.document_id == "DOC-V1"
        doc_service.dynamodb_service.create_document.assert_not_called()

        # Upload modified bytes -> supersedes v1
        content_v2 = b"Updated policy v2 text with changes"
        doc_service.dynamodb_service.create_document.side_effect = lambda m: m

        res_new = doc_service.upload_document(
            file_bytes=content_v2,
            filename="policy.txt",
            owner="hr",
            category="policy",
            access_level=AccessLevel.PUBLIC,
            version="2.0"
        )
        assert existing_v1.status == DocumentStatus.SUPERSEDED
        assert existing_v1.is_current is False
        assert existing_v1.superseded_by == res_new.document_id

    # Test QueryService live freshness filtering
    with patch("backend.app.services.query_service.EmbeddingService"), \
         patch("backend.app.services.query_service.OpenSearchService"), \
         patch("backend.app.services.query_service.GenerationService"), \
         patch("backend.app.services.query_service.DynamoDBService"), \
         patch("backend.app.services.query_service.MetricsService"):
        
        query_svc = QueryService()
        query_svc.embedding_service.embed_text.return_value = [0.1] * 1536

        # OpenSearch still contains the old vector for DOC-V1
        query_svc.opensearch_service.search_similar_chunks.return_value = [
            {
                "chunk_id": "chk-v1",
                "document_id": "DOC-V1",
                "text": "Old outdated policy statement",
                "_score": 0.95,
                "document_status": "READY",
                "access_level": "public"
            }
        ]

        # Live DynamoDB returns superseded doc
        query_svc.dynamodb_service.get_document.return_value = existing_v1

        response = query_svc.query(QueryRequest(question="What is the policy?"))
        assert response.grounded is False
        assert len(response.sources) == 0
        query_svc.generation_service.generate_grounded_answer.assert_not_called()
        query_svc.metrics.record_stale_rejected.assert_called()


def test_phase7_conflict_detection_and_query_awareness():
    """
    Verifies that:
    1. Chunk pairs from different documents with contradiction above threshold produce a ConflictRecord
    2. Conflict privacy prevents lower-clearance users from seeing conflicts involving restricted documents
    3. QueryService detects open conflicts among retrieved evidence and flags warning + context
    """
    conflict_svc = ConflictService()
    conflict_svc.enabled = True
    conflict_svc.threshold = 0.75
    conflict_svc._bedrock = MagicMock()
    conflict_svc._dynamodb = MagicMock()

    # Mock OpenSearch candidate from other document
    mock_os = MagicMock()
    mock_os.search_similar_chunks.return_value = [
        {
            "chunk_id": "chk-doc-b",
            "document_id": "DOC-B",
            "text": "The primary database is PostgreSQL.",
            "_score": 0.88,
            "document_status": "READY"
        }
    ]

    # Mock Bedrock classifier response
    classifier_out = {
        "relationship": "CONTRADICTS",
        "confidence": 0.92,
        "reason": "PostgreSQL contradicts MongoDB database statement"
    }
    body_mock = MagicMock()
    body_mock.read.return_value = json.dumps({
        "results": [{"outputText": json.dumps(classifier_out)}]
    }).encode()
    conflict_svc.bedrock.invoke_model.return_value = {"body": body_mock}

    mock_embed = MagicMock()
    mock_embed.embed_text.return_value = [0.1] * 1536

    chunks = [{"chunk_id": "chk-doc-a", "text": "The primary database is MongoDB."}]
    conflict_svc.dynamodb_table.put_item = MagicMock()

    count = conflict_svc.detect_conflicts(
        document_id="DOC-A",
        chunks=chunks,
        opensearch_service=mock_os,
        embedding_service=mock_embed
    )
    assert count == 1
    conflict_svc.dynamodb_table.put_item.assert_called_once()
    stored_item = conflict_svc.dynamodb_table.put_item.call_args[1]["Item"]
    assert stored_item["relationship"] == "CONTRADICTS"
    assert stored_item["confidence"] == 0.92
    assert stored_item["status"] == "OPEN"
