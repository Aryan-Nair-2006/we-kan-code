import pytest
import json
from unittest.mock import patch, MagicMock
from lambdas.indexing.handler import lambda_handler
from shared.constants.document_status import DocumentStatus

@pytest.fixture
def mock_dependencies():
    with patch('lambdas.indexing.handler.document_service') as mock_doc_svc, \
         patch('lambdas.indexing.handler.s3_service') as mock_s3_svc, \
         patch('lambdas.indexing.handler.dynamodb_service') as mock_dyn_svc, \
         patch('lambdas.indexing.handler.embedding_service') as mock_emb_svc, \
         patch('lambdas.indexing.handler.opensearch_service') as mock_os_svc, \
         patch('backend.app.services.conflict_service.ConflictService') as mock_conflict_svc:

         # ConflictService.detect_conflicts returns 0 by default — non-blocking
         mock_conflict_svc.return_value.detect_conflicts.return_value = 0

         yield {
             "doc": mock_doc_svc,
             "s3": mock_s3_svc,
             "dyn": mock_dyn_svc,
             "emb": mock_emb_svc,
             "os": mock_os_svc,
             "conflict": mock_conflict_svc,
         }

def test_handler_successful_indexing(mock_dependencies):
    event = {
        "Records": [{
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "processed/text/DOC-123/chunks.json"}
            }
        }]
    }
    
    # Mock Document
    mock_doc = MagicMock()
    mock_doc.document_id = "DOC-123"
    mock_doc.status = DocumentStatus.READY
    mock_doc.filename = "test.pdf"
    mock_doc.owner = "user"
    mock_doc.category = "docs"
    mock_doc.access_level = "public"
    mock_doc.version = "1.0"
    mock_doc.created_at = "now"
    mock_doc.updated_at = "now"
    mock_dependencies["doc"].get_document.return_value = mock_doc
    
    # Mock S3 Chunks
    mock_dependencies["s3"].download_processed_chunks.return_value = [
        {"chunk_id": "c1", "chunk_index": 0, "text": "text1"},
        {"chunk_id": "c2", "chunk_index": 1, "text": "text2"}
    ]
    
    # Mock Embeddings
    mock_dependencies["emb"].embed_text.return_value = [0.1, 0.2, 0.3]
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    assert mock_dependencies["emb"].embed_text.call_count == 2
    mock_dependencies["os"].bulk_index_chunks.assert_called_once()
    
    # Verify indexing status updates
    assert mock_doc.indexing_status == "INDEXED"
    assert mock_doc.processing_error is None
    mock_dependencies["dyn"].update_document.assert_called_with(mock_doc)

def test_handler_not_ready_document(mock_dependencies):
    event = {
        "Records": [{
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "processed/text/DOC-123/chunks.json"}
            }
        }]
    }
    
    mock_doc = MagicMock()
    mock_doc.status = DocumentStatus.PROCESSING
    mock_dependencies["doc"].get_document.return_value = mock_doc
    
    lambda_handler(event, None)
    
    mock_dependencies["s3"].download_processed_chunks.assert_not_called()
    mock_dependencies["dyn"].update_document.assert_not_called()

def test_handler_embedding_failure(mock_dependencies):
    event = {
        "Records": [{
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "processed/text/DOC-123/chunks.json"}
            }
        }]
    }
    
    mock_doc = MagicMock()
    mock_doc.status = DocumentStatus.READY
    mock_dependencies["doc"].get_document.return_value = mock_doc
    
    mock_dependencies["s3"].download_processed_chunks.return_value = [
        {"chunk_id": "c1", "chunk_index": 0, "text": "text1"}
    ]
    
    mock_dependencies["emb"].embed_text.side_effect = Exception("Bedrock error")
    
    lambda_handler(event, None)
    
    assert mock_doc.indexing_status == "INDEXING_FAILED"
    assert "Bedrock error" in mock_doc.processing_error
    mock_dependencies["dyn"].update_document.assert_called_with(mock_doc)

def test_handler_url_decoding(mock_dependencies):
    event = {
        "Records": [{
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "processed/text/DOC%20123/chunks.json"}
            }
        }]
    }
    
    mock_doc = MagicMock()
    mock_doc.document_id = "DOC 123"
    mock_doc.status = DocumentStatus.READY
    mock_dependencies["doc"].get_document.return_value = mock_doc
    
    mock_dependencies["s3"].download_processed_chunks.return_value = [
        {"chunk_id": "c1", "chunk_index": 0, "text": "text1"}
    ]
    
    lambda_handler(event, None)
    mock_dependencies["s3"].download_processed_chunks.assert_called_with("DOC 123", "text")

def test_handler_empty_chunks(mock_dependencies):
    event = {
        "Records": [{
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "processed/text/DOC-123/chunks.json"}
            }
        }]
    }
    
    mock_doc = MagicMock()
    mock_doc.status = DocumentStatus.READY
    mock_dependencies["doc"].get_document.return_value = mock_doc
    
    mock_dependencies["s3"].download_processed_chunks.return_value = [
        {"chunk_id": "c1", "chunk_index": 0, "text": "  "},
        {"chunk_id": "c2", "chunk_index": 1, "text": ""}
    ]
    
    lambda_handler(event, None)
    assert mock_doc.indexing_status == "INDEXING_FAILED"
    assert "All chunks in the document were empty or invalid" in mock_doc.processing_error

def test_handler_partial_empty_chunks(mock_dependencies):
    event = {
        "Records": [{
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "processed/text/DOC-123/chunks.json"}
            }
        }]
    }
    
    mock_doc = MagicMock()
    mock_doc.document_id = "DOC-123"
    mock_doc.status = DocumentStatus.READY
    mock_doc.filename = "test.pdf"
    mock_doc.owner = "user"
    mock_doc.category = "docs"
    mock_doc.access_level = "public"
    mock_doc.version = "1.0"
    mock_doc.created_at = "now"
    mock_doc.updated_at = "now"
    mock_dependencies["doc"].get_document.return_value = mock_doc
    
    mock_dependencies["s3"].download_processed_chunks.return_value = [
        {"chunk_id": "c1", "chunk_index": 0, "text": "  "},
        {"chunk_id": "c2", "chunk_index": 1, "text": "valid"}
    ]
    mock_dependencies["emb"].embed_text.return_value = [0.1, 0.2]
    
    lambda_handler(event, None)
    assert mock_doc.indexing_status == "INDEXED"
    # Should only embed the valid one
    assert mock_dependencies["emb"].embed_text.call_count == 1
