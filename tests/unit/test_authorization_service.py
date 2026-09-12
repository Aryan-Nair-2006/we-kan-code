"""
Phase 7 Tests — Access Control / Authorization Service

Tests 1-7 covering:
1. Authenticated user can access public document
2. Team user can access team document
3. Unauthorized user cannot access restricted document
4. Developer cannot access admin-only document
5. Missing authentication fails closed
6. Invalid role fails closed
7. Frontend-supplied access level cannot escalate privileges
"""
import pytest
import os
from unittest.mock import patch, MagicMock

from backend.app.models.auth import AuthContext
from backend.app.services.authorization_service import AuthorizationService
from shared.constants.access_level import AccessLevel


@pytest.fixture
def local_auth_service():
    """AuthorizationService in local dev mode."""
    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_USER_ID": "test-user", "DEV_ROLE": "developer"}):
        svc = AuthorizationService()
        svc.environment = "local"
        return svc


@pytest.fixture
def prod_auth_service():
    """AuthorizationService in production mode."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        svc = AuthorizationService()
        svc.environment = "production"
        return svc


# Test 1: Authenticated user can access public document
def test_public_user_can_access_public_document(local_auth_service):
    with patch.dict(os.environ, {"DEV_ROLE": "public"}):
        local_auth_service.environment = "local"
        svc = AuthorizationService()
        svc.environment = "local"
        with patch.dict(os.environ, {"DEV_ROLE": "public", "DEV_USER_ID": "user1"}):
            ctx = svc.build_auth_context()
    assert svc.is_document_authorized(ctx, "public") is True


# Test 2: Team user can access team document
def test_team_user_can_access_team_document():
    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "team", "DEV_USER_ID": "user2"}):
        svc = AuthorizationService()
        svc.environment = "local"
        ctx = svc.build_auth_context()
    assert svc.is_document_authorized(ctx, "team") is True
    assert svc.is_document_authorized(ctx, "public") is True
    # Team user cannot access developer or admin docs
    assert svc.is_document_authorized(ctx, "developer") is False
    assert svc.is_document_authorized(ctx, "admin") is False


# Test 3: Unauthorized user cannot access restricted document
def test_public_user_cannot_access_developer_document():
    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "public", "DEV_USER_ID": "user3"}):
        svc = AuthorizationService()
        svc.environment = "local"
        ctx = svc.build_auth_context()
    assert svc.is_document_authorized(ctx, "developer") is False
    assert svc.is_document_authorized(ctx, "admin") is False
    assert svc.is_document_authorized(ctx, "team") is False


# Test 4: Developer cannot access admin-only document
def test_developer_cannot_access_admin_document():
    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "developer", "DEV_USER_ID": "dev1"}):
        svc = AuthorizationService()
        svc.environment = "local"
        ctx = svc.build_auth_context()
    assert svc.is_document_authorized(ctx, "developer") is True
    assert svc.is_document_authorized(ctx, "admin") is False


# Test 5: Missing authentication fails closed (production mode, no Authorization header)
def test_missing_authentication_fails_closed(prod_auth_service):
    mock_request = MagicMock()
    mock_request.headers = {}
    with pytest.raises(ValueError, match="Missing or malformed Authorization header"):
        prod_auth_service.build_auth_context(mock_request)


# Test 6: Invalid role defaults to public (fail-closed, not admin)
def test_invalid_role_defaults_to_public():
    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "superadmin", "DEV_USER_ID": "hacker"}):
        svc = AuthorizationService()
        svc.environment = "local"
        ctx = svc.build_auth_context()
    # Invalid role should be downgraded to "public" — fail-closed
    assert ctx.role == "public"
    assert AccessLevel.ADMIN not in ctx.access_levels
    assert AccessLevel.DEVELOPER not in ctx.access_levels


# Test 7: Frontend-supplied access level cannot escalate privileges (query override)
def test_frontend_access_level_overridden_by_auth_context():
    """
    Verifies that when an AuthContext is provided, QueryService uses the AuthContext
    access levels — not the frontend-supplied request.access_levels.
    """
    from unittest.mock import patch, MagicMock
    from shared.models.query import QueryRequest
    from backend.app.services.query_service import QueryService

    # Simulate frontend sending admin access claim
    request = QueryRequest(
        question="What is the secret admin data?",
        access_levels=[AccessLevel.ADMIN]
    )

    # But the real AuthContext (from JWT) only grants public access
    auth_ctx = AuthContext(
        user_id="attacker",
        role="public",
        access_levels=[AccessLevel.PUBLIC]
    )

    with patch("backend.app.services.query_service.EmbeddingService"), \
         patch("backend.app.services.query_service.OpenSearchService"), \
         patch("backend.app.services.query_service.GenerationService"), \
         patch("backend.app.services.query_service.DynamoDBService"), \
         patch("backend.app.services.query_service.MetricsService"):
        svc = QueryService()
        svc.embedding_service.embed_text.return_value = [0.1] * 1536
        # Return an admin chunk from OpenSearch
        svc.opensearch_service.search_similar_chunks.return_value = [
            {
                "chunk_id": "secret-1", "document_id": "admin-doc",
                "text": "Admin secret data", "_score": 0.9,
                "document_status": "READY", "access_level": "admin"
            }
        ]
        svc.dynamodb_service.get_document.return_value = None  # Not found → fail closed

        response = svc.query(request, auth_context=auth_ctx)

    # Admin chunk should be filtered out — attacker gets no answer
    assert response.grounded is False
    assert len(response.sources) == 0


def test_build_auth_context_from_event_authorizer_claims():
    """Verifies that API Gateway authorizer claims in event are correctly parsed."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        svc = AuthorizationService()
        svc.environment = "production"
        event = {
            "requestContext": {
                "authorizer": {
                    "jwt": {
                        "claims": {
                            "sub": "user-123",
                            "email": "user@example.com",
                            "custom:role": "developer"
                        }
                    }
                }
            }
        }
        ctx = svc.build_auth_context_from_event(event)
        assert ctx.user_id == "user-123"
        assert ctx.role == "developer"
        assert AccessLevel.DEVELOPER in ctx.access_levels
        assert AccessLevel.PUBLIC in ctx.access_levels
        assert AccessLevel.ADMIN not in ctx.access_levels


def test_build_auth_context_from_event_missing_auth_fails_closed():
    """Verifies that missing auth in event raises ValueError in production."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        svc = AuthorizationService()
        svc.environment = "production"
        event = {"requestContext": {}, "headers": {}}
        with pytest.raises(ValueError, match="Missing or invalid authentication"):
            svc.build_auth_context_from_event(event)


def test_query_service_fails_closed_in_production_without_auth_context():
    """Verifies that QueryService raises ValueError if called without AuthContext in production."""
    from shared.models.query import QueryRequest
    from backend.app.services.query_service import QueryService

    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        with patch("backend.app.services.query_service.EmbeddingService"), \
             patch("backend.app.services.query_service.OpenSearchService"), \
             patch("backend.app.services.query_service.GenerationService"), \
             patch("backend.app.services.query_service.DynamoDBService"), \
             patch("backend.app.services.query_service.MetricsService"):
            svc = QueryService()
            request = QueryRequest(question="Test question?", access_levels=[AccessLevel.PUBLIC])
            with pytest.raises(ValueError, match="Authentication context is required in production"):
                svc.query(request, auth_context=None)


def test_conflict_privacy_filtering_hides_unauthorized_conflict():
    """Verifies that conflicts involving documents higher than caller's clearance are hidden."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from shared.models.document import ConflictRecord, DocumentMetadata
    from shared.constants.document_status import DocumentStatus

    client = TestClient(app)

    public_doc = DocumentMetadata(
        document_id="doc-pub",
        filename="public.txt",
        file_type="txt",
        owner="alice",
        category="general",
        created_at="2026-09-13T00:00:00Z",
        updated_at="2026-09-13T00:00:00Z",
        access_level=AccessLevel.PUBLIC,
        status=DocumentStatus.READY,
        version="1",
        content_hash="hash1"
    )
    admin_doc = DocumentMetadata(
        document_id="doc-adm",
        filename="secret.txt",
        file_type="txt",
        owner="bob",
        category="finance",
        created_at="2026-09-13T00:00:00Z",
        updated_at="2026-09-13T00:00:00Z",
        access_level=AccessLevel.ADMIN,
        status=DocumentStatus.READY,
        version="1",
        content_hash="hash2"
    )

    conflict = ConflictRecord(
        conflict_id="c-1",
        source_document_id="doc-pub",
        source_chunk_id="chk-pub-1",
        conflicting_document_id="doc-adm",
        conflicting_chunk_id="chk-adm-1",
        relationship="CONTRADICTS",
        confidence=0.85,
        topic="Revenue",
        detected_at="2026-09-13T00:00:00Z",
        status="OPEN"
    )

    with patch("backend.app.services.conflict_service.ConflictService.list_conflicts", return_value=[conflict]), \
         patch("backend.app.services.dynamodb_service.DynamoDBService.get_document") as mock_get_doc:

        def get_doc_side_effect(doc_id):
            if doc_id == "doc-pub":
                return public_doc
            elif doc_id == "doc-adm":
                return admin_doc
            return None
        mock_get_doc.side_effect = get_doc_side_effect

        # 1. As Public user -> should NOT see conflict involving admin doc
        with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "public"}):
            resp = client.get("/conflicts")
            assert resp.status_code == 200
            assert resp.json() == []

        # 2. As Admin user -> should see conflict
        with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "admin"}):
            resp = client.get("/conflicts")
            assert resp.status_code == 200
            assert len(resp.json()) == 1
            assert resp.json()[0]["conflict_id"] == "c-1"


def test_document_metadata_access_control():
    """Verifies that GET /documents and GET /documents/{id} enforce role clearance."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from shared.models.document import DocumentMetadata
    from shared.constants.document_status import DocumentStatus

    client = TestClient(app)

    public_doc = DocumentMetadata(
        document_id="doc-pub",
        filename="public.txt",
        file_type="txt",
        owner="alice",
        category="general",
        created_at="2026-09-13T00:00:00Z",
        updated_at="2026-09-13T00:00:00Z",
        access_level=AccessLevel.PUBLIC,
        status=DocumentStatus.READY,
        version="1",
        content_hash="hash1"
    )
    admin_doc = DocumentMetadata(
        document_id="doc-adm",
        filename="secret.txt",
        file_type="txt",
        owner="bob",
        category="finance",
        created_at="2026-09-13T00:00:00Z",
        updated_at="2026-09-13T00:00:00Z",
        access_level=AccessLevel.ADMIN,
        status=DocumentStatus.READY,
        version="1",
        content_hash="hash2"
    )

    with patch("backend.app.services.document_service.DocumentService.list_documents", return_value=[public_doc, admin_doc]), \
         patch("backend.app.services.document_service.DocumentService.get_document") as mock_get_doc:

        mock_get_doc.side_effect = lambda doc_id: admin_doc if doc_id == "doc-adm" else public_doc

        # As Public user:
        with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "public"}):
            resp = client.get("/documents")
            assert resp.status_code == 200
            docs = resp.json()
            assert len(docs) == 1
            assert docs[0]["document_id"] == "doc-pub"

            # Accessing admin doc directly -> 403
            resp_adm = client.get("/documents/doc-adm")
            assert resp_adm.status_code == 403


def test_public_user_cannot_view_or_resolve_reviews():
    """Verifies that public users cannot list or resolve reviews, but developers can."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from shared.models.document import FlagRecord

    client = TestClient(app)

    flag = FlagRecord(
        flag_id="flg-1",
        document_id="doc-1",
        reason="Needs review",
        status="OPEN",
        created_at="2026-09-13T00:00:00Z"
    )

    with patch("backend.app.services.review_service.ReviewService.list_flags", return_value=[flag]), \
         patch("backend.app.services.review_service.ReviewService.resolve_flag", return_value=flag):

        # Public user cannot list reviews
        with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "public"}):
            resp = client.get("/reviews")
            assert resp.status_code == 403

            resp_res = client.post("/reviews/flg-1/resolve", json={"resolution": "DISMISSED", "notes": "ok"})
            assert resp_res.status_code == 403

def test_unauthenticated_requests_fail_closed_with_401():
    """Verifies that unauthenticated requests to protected endpoints return 401 in production mode."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from io import BytesIO

    client = TestClient(app)

    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        # 1. GET /documents
        resp = client.get("/documents")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Authentication required"

        # 2. GET /documents/{id}
        resp = client.get("/documents/doc-1")
        assert resp.status_code == 401

        # 3. GET /documents/{id}/freshness
        resp = client.get("/documents/doc-1/freshness")
        assert resp.status_code == 401

        # 4. POST /documents/upload
        files = {"file": ("test.txt", BytesIO(b"abc"), "text/plain")}
        resp = client.post("/documents/upload", files=files, data={"owner": "alice", "category": "general", "access_level": "public", "version": "1"})
        assert resp.status_code == 401

        # 5. POST /flags
        resp = client.post("/flags", json={"document_id": "doc-1", "reason": "inaccurate"})
        assert resp.status_code == 401

        # 6. GET /reviews
        resp = client.get("/reviews")
        assert resp.status_code == 401

        # 7. POST /reviews/{id}/resolve
        resp = client.post("/reviews/flg-1/resolve", json={"resolution": "DISMISSED"})
        assert resp.status_code == 401

        # 8. GET /conflicts
        resp = client.get("/conflicts")
        assert resp.status_code == 401

        # 9. GET /documents/{id}/conflicts
        resp = client.get("/documents/doc-1/conflicts")
        assert resp.status_code == 401


def test_document_upload_permissions():
    """Verifies that public users cannot upload (403) and team users can upload."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from io import BytesIO
    from shared.models.document import DocumentMetadata
    from shared.constants.document_status import DocumentStatus

    client = TestClient(app)

    # Public user upload -> 403
    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "public"}):
        file_content = b"Sample text content"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
        data = {"owner": "user", "category": "general", "access_level": "public", "version": "1"}
        resp = client.post("/documents/upload", files=files, data=data)
        assert resp.status_code == 403
        assert "Public users are not authorized" in resp.json()["detail"]

    # Team user upload -> allowed
    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "team"}), \
         patch("backend.app.services.document_service.DocumentService.upload_document") as mock_upload:
        mock_upload.return_value = DocumentMetadata(
            document_id="doc-new",
            filename="test.txt",
            file_type="txt",
            owner="user",
            category="general",
            created_at="2026-09-13T00:00:00Z",
            updated_at="2026-09-13T00:00:00Z",
            access_level=AccessLevel.TEAM,
            status=DocumentStatus.READY,
            version="1"
        )
        file_content = b"Sample text content"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
        data = {"owner": "user", "category": "general", "access_level": "team", "version": "1"}
        resp = client.post("/documents/upload", files=files, data=data)
        assert resp.status_code == 200
        assert resp.json()["document_id"] == "doc-new"


def test_authenticated_flag_allowed():
    """Verifies that any authenticated user can create a flag."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from shared.models.document import FlagRecord

    client = TestClient(app)

    flag_out = FlagRecord(
        flag_id="flg-1",
        document_id="doc-1",
        reason="Check this passage",
        status="OPEN",
        created_at="2026-09-13T00:00:00Z"
    )

    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "public"}), \
         patch("backend.app.services.review_service.ReviewService.create_flag", return_value=flag_out):
        resp = client.post("/flags", json={"document_id": "doc-1", "reason": "Check this passage"})
        assert resp.status_code == 200
        assert resp.json()["flag_id"] == "flg-1"



