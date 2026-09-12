import pytest
import json
from unittest.mock import patch, MagicMock
from lambdas.ingestion.handler import lambda_handler
from shared.constants.document_status import DocumentStatus
from shared.models.document import DocumentMetadata
from shared.constants.access_level import AccessLevel

@patch('lambdas.ingestion.handler.dynamodb_service')
@patch('lambdas.ingestion.handler.s3_service')
def test_lambda_handler_success(mock_s3, mock_ddb):
    # Setup mocks
    mock_doc = DocumentMetadata(
        document_id="DOC-123",
        filename="test.txt",
        file_type="txt",
        owner="test",
        category="test",
        access_level=AccessLevel.PUBLIC,
        version="1.0",
        created_at="now",
        updated_at="now",
        status=DocumentStatus.UPLOADED,
        s3_key="documents/raw/DOC-123/test.txt"
    )
    mock_ddb.get_document.return_value = mock_doc
    mock_s3.download_file.return_value = b"Hello world! This is a test."
    
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "documents/raw/DOC-123/test%20space.txt"}
                }
            }
        ]
    }
    
    response = lambda_handler(event, {})
    
    assert response["statusCode"] == 200
    
    # Check that status was updated to PROCESSING then READY
    assert mock_ddb.update_document.call_count == 2
    final_call_args = mock_ddb.update_document.call_args_list[-1][0][0]
    assert final_call_args.status == DocumentStatus.READY
    assert final_call_args.chunk_count > 0
    
    # Check that processed chunks were written to S3
    mock_s3.put_processed_text.assert_called_once()
    args, kwargs = mock_s3.put_processed_text.call_args
    assert args[0] == "DOC-123"
    assert "chunks" in args[1]
    
@patch('lambdas.ingestion.handler.dynamodb_service')
@patch('lambdas.ingestion.handler.s3_service')
def test_lambda_handler_empty_doc(mock_s3, mock_ddb):
    mock_doc = DocumentMetadata(
        document_id="DOC-123",
        filename="test.txt",
        file_type="txt",
        owner="test",
        category="test",
        access_level=AccessLevel.PUBLIC,
        version="1.0",
        created_at="now",
        updated_at="now",
        status=DocumentStatus.UPLOADED,
        s3_key="documents/raw/DOC-123/test.txt"
    )
    mock_ddb.get_document.return_value = mock_doc
    # empty file
    mock_s3.download_file.return_value = b"   \n "
    
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "documents/raw/DOC-123/test.txt"}
                }
            }
        ]
    }
    
    lambda_handler(event, {})
    
    # Should be FAILED
    final_call_args = mock_ddb.update_document.call_args_list[-1][0][0]
    assert final_call_args.status == DocumentStatus.FAILED
    assert "no extractable text" in final_call_args.processing_error

@patch('lambdas.ingestion.handler.dynamodb_service')
@patch('lambdas.ingestion.handler.s3_service')
def test_lambda_handler_already_ready(mock_s3, mock_ddb):
    mock_doc = DocumentMetadata(
        document_id="DOC-123",
        filename="test.txt",
        file_type="txt",
        owner="test",
        category="test",
        access_level=AccessLevel.PUBLIC,
        version="1.0",
        created_at="now",
        updated_at="now",
        status=DocumentStatus.READY, # ALREADY READY
        s3_key="documents/raw/DOC-123/test.txt"
    )
    mock_ddb.get_document.return_value = mock_doc
    
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "documents/raw/DOC-123/test.txt"}
                }
            }
        ]
    }
    
    lambda_handler(event, {})
    
    # Should exit early without updating
    mock_ddb.update_document.assert_not_called()
    mock_s3.download_file.assert_not_called()
