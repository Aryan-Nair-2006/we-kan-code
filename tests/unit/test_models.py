import pytest
from pydantic import ValidationError
from shared.models.document import DocumentMetadata, AccessLevel, DocumentStatus

def test_document_metadata_valid():
    doc = DocumentMetadata(
        document_id="DOC-123",
        filename="test.pdf",
        file_type="pdf",
        owner="Alice",
        category="design",
        created_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-01T00:00:00Z",
        version="1.0",
        access_level=AccessLevel.TEAM,
        status=DocumentStatus.UPLOADED
    )
    assert doc.document_id == "DOC-123"
    assert doc.access_level == "team"
    assert doc.status == "uploaded"

def test_document_metadata_invalid_status():
    with pytest.raises(ValidationError):
        DocumentMetadata(
            document_id="DOC-123",
            filename="test.pdf",
            file_type="pdf",
            owner="Alice",
            category="design",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            version="1.0",
            access_level=AccessLevel.TEAM,
            status="invalid_status"
        )
