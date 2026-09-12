import pytest
from unittest.mock import patch, MagicMock
from backend.app.services.opensearch_service import OpenSearchService
from shared.models.indexing import IndexedChunk

@pytest.fixture
def mock_opensearch():
    with patch('backend.app.services.opensearch_service.OpenSearch') as mock_os:
        mock_client = MagicMock()
        mock_os.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_helpers():
    with patch('opensearchpy.helpers.bulk') as mock_bulk:
        yield mock_bulk

def test_initialize_index_creates(mock_opensearch):
    mock_opensearch.indices.exists.return_value = False
    
    service = OpenSearchService(host="test-host")
    service.client = mock_opensearch
    service.initialize_index()
    
    mock_opensearch.indices.create.assert_called_once()

def test_initialize_index_exists(mock_opensearch):
    mock_opensearch.indices.exists.return_value = True
    
    service = OpenSearchService(host="test-host")
    service.client = mock_opensearch
    service.initialize_index()
    
    mock_opensearch.indices.create.assert_not_called()

def test_bulk_index_success(mock_opensearch, mock_helpers):
    service = OpenSearchService(host="test-host")
    service.client = mock_opensearch
    
    chunk = IndexedChunk(
        chunk_id="chunk1",
        document_id="doc1",
        text="text",
        embedding=[0.1, 0.2],
        chunk_index=0,
        filename="test.pdf",
        owner="test",
        category="test",
        access_level="public",
        version="1.0",
        document_status="READY",
        created_at="now",
        updated_at="now"
    )
    
    mock_helpers.return_value = (1, []) # success count, failed items
    
    service.bulk_index_chunks([chunk])
    mock_helpers.assert_called_once()

def test_bulk_index_failure(mock_opensearch, mock_helpers):
    service = OpenSearchService(host="test-host")
    service.client = mock_opensearch
    
    chunk = IndexedChunk(
        chunk_id="chunk1",
        document_id="doc1",
        text="text",
        embedding=[0.1, 0.2],
        chunk_index=0,
        filename="test.pdf",
        owner="test",
        category="test",
        access_level="public",
        version="1.0",
        document_status="READY",
        created_at="now",
        updated_at="now"
    )
    
    mock_helpers.return_value = (0, [{"index": {"error": "failed"}}])
    
    with pytest.raises(RuntimeError, match="Failed to index"):
        service.bulk_index_chunks([chunk])
