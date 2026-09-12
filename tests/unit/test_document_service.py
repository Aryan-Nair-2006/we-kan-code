import pytest
from unittest.mock import MagicMock, patch
from backend.app.services.document_service import DocumentService
from shared.constants.access_level import AccessLevel
from backend.app.core.exceptions import ValidationError

@patch('backend.app.services.document_service.S3Service')
@patch('backend.app.services.document_service.DynamoDBService')
def test_upload_document_success(mock_ddb, mock_s3):
    mock_ddb_instance = mock_ddb.return_value
    mock_s3_instance = mock_s3.return_value
    
    # Mock create_document to just return what it was given
    mock_ddb_instance.create_document.side_effect = lambda x: x
    
    doc_service = DocumentService()
    
    # Should work for supported type
    result = doc_service.upload_document(
        file_bytes=b"test data",
        filename="test.txt",
        owner="Alice",
        category="Test",
        access_level=AccessLevel.PUBLIC,
        version="1.0"
    )
    
    assert result.filename == "test.txt"
    assert result.document_id.startswith("DOC-")
    assert result.status == "uploaded"
    assert result.s3_key == f"documents/raw/{result.document_id}/test.txt"
    
    # Verify S3 was called with correct metadata
    mock_s3_instance.upload_file.assert_called_once()
    kwargs = mock_s3_instance.upload_file.call_args[1]
    assert kwargs["metadata"]["document_id"] == result.document_id
    assert kwargs["metadata"]["owner"] == "Alice"
    assert kwargs["metadata"]["category"] == "Test"

@patch('backend.app.services.document_service.S3Service')
@patch('backend.app.services.document_service.DynamoDBService')
def test_upload_document_unsupported_type(mock_ddb, mock_s3):
    doc_service = DocumentService()
    
    with pytest.raises(ValidationError):
        doc_service.upload_document(
            file_bytes=b"test data",
            filename="test.exe",
            owner="Alice",
            category="Test",
            access_level=AccessLevel.PUBLIC,
            version="1.0"
        )
