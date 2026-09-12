import pytest
import json
import os
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

def test_lambda_handler_success(mock_query_service):
    from shared.models.query import QueryResponse
    event = {'body': json.dumps({'question': 'What is DynamoDB?'})}
    mock_response = QueryResponse(
        question="What is DynamoDB?",
        answer="DynamoDB is a NoSQL database.",
        sources=[],
        grounded=True,
        execution_time_seconds=0.1
    )
    mock_query_service.query.return_value = mock_response

    response = lambda_handler(event, None)
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['grounded'] is True
    assert body['answer'] == "DynamoDB is a NoSQL database."

def test_lambda_handler_auth_failure_in_production():
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        with patch('lambdas.query.handler.get_auth_service') as mock_get_auth:
            mock_auth = MagicMock()
            mock_auth.build_auth_context_from_event.side_effect = ValueError("Missing or invalid authentication")
            mock_get_auth.return_value = mock_auth
            
            event = {'body': json.dumps({'question': 'Hello?'})}
            response = lambda_handler(event, None)
            assert response['statusCode'] == 401
            body = json.loads(response['body'])
            assert 'Authentication required' in body['error']
