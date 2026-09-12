import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from shared.constants.access_level import AccessLevel
from shared.constants.document_status import DocumentStatus
from shared.models.document import DocumentMetadata, FlagRecord
from shared.models.query import QueryResponse, SourceCitation

client = TestClient(app)


def test_phase6_full_e2e_question_flag_review_resolve_lifecycle():
    """
    End-to-End Test for Phase 6:
    1. User asks a question -> gets grounded answer + citations
    2. User flags the answer with reasons & context -> POST /flags
    3. Flag is persisted with full metadata and document marked PENDING_REVIEW
    4. Reviewer retrieves the flag queue -> GET /reviews?status=OPEN
    5. Reviewer inspects context & resolves -> POST /reviews/{flag_id}/resolve
    6. Flag status transitions to RESOLVED/DISMISSED and document unblocks to READY
    """
    doc_id = "DOC-E2E-101"
    chunk_id = "CHUNK-E2E-501"

    # In-memory storage simulation for DynamoDB
    db_docs = {
        doc_id: DocumentMetadata(
            document_id=doc_id,
            filename="user_manual.pdf",
            file_type="pdf",
            owner="documentation-team",
            category="guides",
            created_at="2026-09-13T00:00:00Z",
            updated_at="2026-09-13T00:00:00Z",
            access_level=AccessLevel.PUBLIC,
            status=DocumentStatus.READY,
            version="1.0"
        )
    }
    db_flags = {}

    def mock_get_doc(id_):
        return db_docs.get(id_)

    def mock_update_doc(doc):
        db_docs[doc.document_id] = doc
        return doc

    def mock_put_flag_item(Item):
        rec = FlagRecord(**Item)
        db_flags[rec.flag_id] = rec

    def mock_get_flag_item(Key):
        flag = db_flags.get(Key.get("flag_id"))
        return {"Item": flag.model_dump(mode="json")} if flag else {}

    def mock_scan_flags():
        return {"Items": [f.model_dump(mode="json") for f in db_flags.values()]}

    # Step 1: User asks a question
    with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "team", "DEV_USER_ID": "user-bob"}):
        mock_query_resp = QueryResponse(
            question="How do I configure OAuth?",
            answer="Set COGNITO_USER_POOL_ID in your environment variables. [S1]",
            grounded=True,
            confidence=0.92,
            sources=[
                SourceCitation(
                    document_id=doc_id,
                    filename="user_manual.pdf",
                    chunk_id=chunk_id,
                    similarity=0.92,
                    text="Set COGNITO_USER_POOL_ID in your environment variables."
                )
            ]
        )

        with patch("backend.app.services.query_service.QueryService.query", return_value=mock_query_resp):
            q_resp = client.post("/query", json={"question": "How do I configure OAuth?"})
            assert q_resp.status_code == 200
            q_data = q_resp.json()
            assert q_data["grounded"] is True
            assert len(q_data["sources"]) == 1

        # Step 2: User flags the answer
        with patch("backend.app.services.dynamodb_service.DynamoDBService.get_document", side_effect=mock_get_doc), \
             patch("backend.app.services.dynamodb_service.DynamoDBService.update_document", side_effect=mock_update_doc), \
             patch("backend.app.main.review_service.table") as mock_table:

            mock_table.put_item.side_effect = mock_put_flag_item
            mock_table.get_item.side_effect = mock_get_flag_item
            mock_table.scan.side_effect = mock_scan_flags

            flag_req = {
                "document_id": doc_id,
                "chunk_id": chunk_id,
                "reason": "Outdated information",
                "details": "Cognito config moved to template.yaml in Phase 8.",
                "question": q_data["question"],
                "answer": q_data["answer"],
                "source_filename": "user_manual.pdf",
                "supporting_passage": q_data["sources"][0]["text"]
            }

            flag_resp = client.post("/flags", json=flag_req)
            assert flag_resp.status_code == 200
            flag_data = flag_resp.json()
            flag_id = flag_data["flag_id"]

            # Step 3: Verify flag persistence & doc status transition to PENDING_REVIEW
            assert flag_data["status"] == "OPEN"
            assert flag_data["flagged_by"] == "user-bob"
            assert flag_data["reason"] == "Outdated information"
            assert db_docs[doc_id].status == DocumentStatus.PENDING_REVIEW

            # Step 4: Reviewer retrieves pending flags
            with patch.dict(os.environ, {"ENVIRONMENT": "local", "DEV_ROLE": "admin", "DEV_USER_ID": "admin-sarah"}):
                list_resp = client.get("/reviews?status=OPEN")
                assert list_resp.status_code == 200
                open_list = list_resp.json()
                assert len(open_list) == 1
                assert open_list[0]["flag_id"] == flag_id
                assert open_list[0]["question"] == "How do I configure OAuth?"
                assert open_list[0]["details"] == "Cognito config moved to template.yaml in Phase 8."

                # Step 5: Reviewer resolves the flag
                resolve_req = {
                    "resolution": "CORRECTED",
                    "notes": "Updated documentation reference in template.yaml."
                }
                resolve_resp = client.post(f"/reviews/{flag_id}/resolve", json=resolve_req)
                assert resolve_resp.status_code == 200
                res_data = resolve_resp.json()
                assert res_data["status"] == "RESOLVED"
                assert res_data["resolution"] == "CORRECTED"
                assert res_data["reviewer"] == "admin-sarah"
                assert res_data["notes"] == "Updated documentation reference in template.yaml."
                assert res_data["resolved_at"] is not None

                # Step 6: Verify document is unblocked back to READY
                assert db_docs[doc_id].status == DocumentStatus.READY

                # Step 7: Verify open queue is now empty and resolved queue contains the record
                open_check = client.get("/reviews?status=OPEN").json()
                assert len(open_check) == 0

                resolved_check = client.get("/reviews?status=RESOLVED").json()
                assert len(resolved_check) == 1
                assert resolved_check[0]["flag_id"] == flag_id
