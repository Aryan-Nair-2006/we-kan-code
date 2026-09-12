import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from shared.constants.access_level import AccessLevel
from shared.constants.document_status import DocumentStatus
from shared.models.document import DocumentMetadata, FlagRecord, FlagRequest, ResolveFlagRequest
from backend.app.services.review_service import ReviewService

client = TestClient(app)


def test_unauthenticated_flag_creation_returns_401():
    """Unauthenticated requests in production environment must fail closed with 401."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        resp = client.post("/flags", json={"document_id": "doc-1", "reason": "Inaccurate information"})
        assert resp.status_code == 401
        assert "Authentication required" in resp.json()["detail"]


def test_malformed_flag_request_returns_422():
    """Malformed request (missing required 'document_id' or 'reason') returns 422."""
    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "team"}):
        resp = client.post("/flags", json={"only_details": "No document id provided"})
        assert resp.status_code == 422


def test_authenticated_user_creates_flag_with_full_context():
    """Authenticated user creates a flag that captures full question, answer, and reason context."""
    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "team", "DEV_USER_ID": "user-alice"}):
        with patch("backend.app.services.dynamodb_service.DynamoDBService.get_document") as mock_get_doc, \
             patch("backend.app.services.dynamodb_service.DynamoDBService.update_document") as mock_update_doc, \
             patch("backend.app.services.review_service.ReviewService.get_flag") as mock_get_flag:
            
            mock_doc = DocumentMetadata(
                document_id="doc-123",
                filename="architecture.pdf",
                file_type="pdf",
                owner="arch-team",
                category="engineering",
                created_at="2026-09-13T00:00:00Z",
                updated_at="2026-09-13T00:00:00Z",
                access_level=AccessLevel.TEAM,
                status=DocumentStatus.READY,
                version="1.0"
            )
            mock_get_doc.return_value = mock_doc

            payload = {
                "document_id": "doc-123",
                "chunk_id": "chunk-456",
                "reason": "Outdated information",
                "details": "The port number mentioned was changed to 8000.",
                "question": "What port does the backend run on?",
                "answer": "The backend runs on port 5000 according to [S1].",
                "source_filename": "architecture.pdf",
                "supporting_passage": "The server listens on default port 5000."
            }

            resp = client.post("/flags", json=payload)
            assert resp.status_code == 200
            data = resp.json()

            assert data["document_id"] == "doc-123"
            assert data["chunk_id"] == "chunk-456"
            assert data["reason"] == "Outdated information"
            assert data["details"] == "The port number mentioned was changed to 8000."
            assert data["question"] == "What port does the backend run on?"
            assert data["answer"] == "The backend runs on port 5000 according to [S1]."
            assert data["source_filename"] == "architecture.pdf"
            assert data["supporting_passage"] == "The server listens on default port 5000."
            assert data["flagged_by"] == "user-alice"
            assert data["status"] == "OPEN"
            assert data["flag_id"] is not None
            assert data["created_at"] is not None

            # Verify document was marked PENDING_REVIEW
            mock_update_doc.assert_called_once()
            assert mock_doc.status == DocumentStatus.PENDING_REVIEW


def test_public_user_cannot_view_or_resolve_reviews():
    """Public users must be rejected with 403 on review management endpoints."""
    # List reviews
    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "public"}):
        resp = client.get("/reviews")
        assert resp.status_code == 403
        assert "Insufficient permissions" in resp.json()["detail"]

    # Resolve review
    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "public"}):
        resp = client.post("/reviews/flag-123/resolve", json={"resolution": "CORRECTED"})
        assert resp.status_code == 403
        assert "Insufficient permissions" in resp.json()["detail"]


def test_unauthenticated_review_endpoints_return_401():
    """Unauthenticated requests in production receive 401 on review management."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        resp = client.get("/reviews")
        assert resp.status_code == 401

    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        resp = client.post("/reviews/flag-123/resolve", json={"resolution": "DISMISSED"})
        assert resp.status_code == 401


def test_authorized_reviewer_lists_and_filters_flags():
    """Reviewer (developer/admin) can list flags and filter by status."""
    mock_flags = [
        FlagRecord(
            flag_id="flag-1",
            document_id="doc-1",
            reason="Reason 1",
            status="OPEN",
            created_at="2026-09-13T01:00:00Z"
        ),
        FlagRecord(
            flag_id="flag-2",
            document_id="doc-2",
            reason="Reason 2",
            status="RESOLVED",
            created_at="2026-09-13T00:30:00Z"
        )
    ]

    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "admin"}):
        with patch("backend.app.services.review_service.ReviewService.list_flags", return_value=mock_flags):
            resp = client.get("/reviews")
            assert resp.status_code == 200
            assert len(resp.json()) == 2

        with patch("backend.app.services.review_service.ReviewService.list_flags", return_value=[mock_flags[0]]):
            resp = client.get("/reviews?status=OPEN")
            assert resp.status_code == 200
            items = resp.json()
            assert len(items) == 1
            assert items[0]["flag_id"] == "flag-1"
            assert items[0]["status"] == "OPEN"


def test_resolve_nonexistent_flag_returns_404():
    """Resolving a nonexistent flag returns 404."""
    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "admin"}):
        with patch("backend.app.services.review_service.ReviewService.get_flag", return_value=None):
            resp = client.post("/reviews/nonexistent-flag/resolve", json={"resolution": "CORRECTED"})
            assert resp.status_code == 404
            assert "not found" in resp.json()["detail"].lower()


def test_invalid_resolution_action_rejected_with_400():
    """Resolving with an invalid action (not CORRECTED, DISMISSED, ARCHIVE_DOCUMENT, RESOLVED) returns 400."""
    existing_flag = FlagRecord(
        flag_id="flag-abc",
        document_id="doc-123",
        reason="Wrong passage",
        status="OPEN",
        created_at="2026-09-13T00:00:00Z"
    )

    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "admin"}):
        with patch("backend.app.services.review_service.ReviewService.get_flag", return_value=existing_flag):
            resp = client.post("/reviews/flag-abc/resolve", json={"resolution": "INVALID_ACTION"})
            assert resp.status_code == 400
            assert "Invalid resolution action" in resp.json()["detail"]


def test_authorized_reviewer_resolves_flag_workflow():
    """Reviewer successfully resolves flag with decision, notes, reviewer ID, and timestamp recorded."""
    existing_flag = FlagRecord(
        flag_id="flag-abc",
        document_id="doc-123",
        reason="Outdated",
        status="OPEN",
        created_at="2026-09-13T00:00:00Z"
    )

    mock_doc = DocumentMetadata(
        document_id="doc-123",
        filename="specs.docx",
        file_type="docx",
        owner="eng",
        category="specs",
        created_at="2026-09-13T00:00:00Z",
        updated_at="2026-09-13T00:00:00Z",
        access_level=AccessLevel.TEAM,
        status=DocumentStatus.PENDING_REVIEW,
        version="1.0"
    )

    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "admin", "DEV_USER_ID": "admin-reviewer"}):
        with patch("backend.app.services.review_service.ReviewService.get_flag", return_value=existing_flag), \
             patch("backend.app.services.review_service.ReviewService.list_flags", return_value=[]), \
             patch("backend.app.services.dynamodb_service.DynamoDBService.get_document", return_value=mock_doc), \
             patch("backend.app.services.dynamodb_service.DynamoDBService.update_document") as mock_update_doc:

            payload = {
                "resolution": "CORRECTED",
                "notes": "Verified updated specs have been reviewed."
            }
            resp = client.post("/reviews/flag-abc/resolve", json=payload)
            assert resp.status_code == 200
            data = resp.json()

            assert data["flag_id"] == "flag-abc"
            assert data["status"] == "RESOLVED"
            assert data["resolution"] == "CORRECTED"
            assert data["reviewer"] == "admin-reviewer"
            assert data["notes"] == "Verified updated specs have been reviewed."
            assert data["resolved_at"] is not None

            # Verify document was unblocked back to READY
            assert mock_doc.status == DocumentStatus.READY
            mock_update_doc.assert_called_once()
