import pytest
import json
from unittest.mock import patch, MagicMock
from lambdas.query.handler import lambda_handler

@pytest.fixture
def mock_query_service():
    with patch('lambdas.query.handler.get_query_service') as mock_get_service:
        mock_svc = MagicMock()
        mock_get_service.return_value = mock_svc
        yield mock_svc

def test_lambda_handler_invalid_json():
    event = {'body': '{invalid json'}
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body

def test_lambda_handler_invalid_request():
    event = {'body': json.dumps({'wrong_field': 'hello'})}
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body

def test_lambda_handler_service_error(mock_query_service):
    event = {'body': json.dumps({'question': 'Hello?'})}
    mock_query_service.query.side_effect = Exception("Internal explosion")
    
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 500
    body = json.loads(response['body'])
    assert body['error'] == 'Internal server error'
    assert 'Internal explosion' not in response['body'] # Do not leak stack traces
