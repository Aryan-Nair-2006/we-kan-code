import json
import logging
import traceback
from pydantic import ValidationError

from backend.app.services.query_service import QueryService
from backend.app.services.authorization_service import AuthorizationService
from shared.models.query import QueryRequest

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize service globally for container reuse
query_service = None
auth_service = None

def get_query_service():
    global query_service
    if query_service is None:
        query_service = QueryService()
    return query_service

def get_auth_service():
    global auth_service
    if auth_service is None:
        auth_service = AuthorizationService()
    return auth_service

def lambda_handler(event, context):
    """
    Lambda handler for answering queries using RAG with backend authorization.
    """
    logger.info("Received query event")
    
    try:
        # Parse body
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
            
        request = QueryRequest(**body)
        
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"Invalid request format: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid request format', 'details': str(e)})
        }
        
    # Derive AuthContext server-side
    try:
        auth_svc = get_auth_service()
        auth_ctx = auth_svc.build_auth_context_from_event(event)
    except ValueError as e:
        logger.warning(f"Authentication failed: {str(e)}")
        return {
            'statusCode': 401,
            'body': json.dumps({'error': 'Authentication required', 'details': str(e)})
        }
        
    try:
        svc = get_query_service()
        response = svc.query(request, auth_context=auth_ctx)
        
        return {
            'statusCode': 200,
            'body': response.model_dump_json()
        }
        
    except Exception as e:
        logger.error(f"Internal server error: {str(e)}")
        # Do not expose stack traces to client
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
