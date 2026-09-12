import boto3
import json
import time
from typing import List
from botocore.exceptions import ClientError
from backend.app.core.config import settings
from backend.app.core.logging import setup_logger

logger = setup_logger(__name__)

class EmbeddingService:
    def __init__(self, model_id: str = settings.bedrock_embedding_model_id, region: str = settings.aws_region):
        self.model_id = model_id
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
        self.max_retries = settings.bedrock_max_retries
        self.dimension = settings.opensearch_vector_dimension

    def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        payload = {
            "inputText": text
        }
        
        for attempt in range(self.max_retries):
            try:
                response = self.bedrock.invoke_model(
                    modelId=self.model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(payload)
                )
                
                response_body = json.loads(response.get('body').read())
                embedding = response_body.get('embedding')
                
                if not embedding or not isinstance(embedding, list):
                    raise ValueError("Malformed embedding response")
                    
                if len(embedding) != self.dimension:
                    raise ValueError(f"Expected dimension {self.dimension}, got {len(embedding)}")
                    
                return embedding
                
            except ClientError as e:
                err_code = e.response.get('Error', {}).get('Code')
                if err_code in ['ThrottlingException', 'ServiceUnavailableException'] and attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                logger.error(f"Bedrock invocation failed: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Failed to generate embedding: {str(e)}")
                raise

        raise RuntimeError("Exhausted retries for embedding generation")
