import json
import logging
import traceback
from pydantic import ValidationError

from backend.app.services.query_service import QueryService
from shared.models.query import QueryRequest

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize service globally for container reuse
query_service = None

def get_query_service():
    global query_service
    if query_service is None:
        query_service = QueryService()
    return query_service

def lambda_handler(event, context):
    """
    Lambda handler for answering queries using RAG.
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
        
    try:
        svc = get_query_service()
        response = svc.query(request)
        
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
