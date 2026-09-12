import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from backend.app.services.embedding_service import EmbeddingService
import json

@pytest.fixture
def mock_bedrock():
    with patch('boto3.client') as mock_client:
        mock_boto = MagicMock()
        mock_client.return_value = mock_boto
        yield mock_boto

def test_embedding_success(mock_bedrock):
    service = EmbeddingService(model_id="test-model")
    service.dimension = 3
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "embedding": [0.1, 0.2, 0.3]
    }).encode('utf-8')
    mock_bedrock.invoke_model.return_value = {'body': mock_response}
    
    result = service.embed_text("test text")
    assert result == [0.1, 0.2, 0.3]

def test_embedding_empty_text():
    service = EmbeddingService()
    with pytest.raises(ValueError, match="Cannot embed empty text"):
        service.embed_text("   ")

def test_embedding_invalid_dimension(mock_bedrock):
    service = EmbeddingService()
    service.dimension = 1536
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "embedding": [0.1, 0.2, 0.3]
    }).encode('utf-8')
    mock_bedrock.invoke_model.return_value = {'body': mock_response}
    
    with pytest.raises(ValueError, match="Expected dimension"):
        service.embed_text("test")

def test_embedding_retry_throttling(mock_bedrock):
    service = EmbeddingService()
    service.dimension = 3
    service.max_retries = 2
    
    # First call fails with Throttling, second succeeds
    error_response = {'Error': {'Code': 'ThrottlingException'}}
    mock_bedrock.invoke_model.side_effect = [
        ClientError(error_response, 'InvokeModel'),
        {'body': MagicMock(read=lambda: json.dumps({"embedding": [0.1, 0.2, 0.3]}).encode('utf-8'))}
    ]
    
    result = service.embed_text("test")
    assert result == [0.1, 0.2, 0.3]
    assert mock_bedrock.invoke_model.call_count == 2
