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

        # Fast path if local and no credentials
        if settings.environment == "local" and boto3.Session().get_credentials() is None:
            import hashlib, math
            h = hashlib.sha256(text.encode("utf-8")).digest()
            vec = [float((h[i % len(h)] + i * 17) % 100) / 100.0 for i in range(self.dimension)]
            norm = math.sqrt(sum(x*x for x in vec)) or 1.0
            return [x / norm for x in vec]

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
                if "NoCredentialsError" in type(e).__name__ or "Unable to locate credentials" in str(e):
                    logger.warning(f"Bedrock credentials not available, using local deterministic embedding: {e}")
                    import hashlib, math
                    h = hashlib.sha256(text.encode("utf-8")).digest()
                    vec = [float((h[i % len(h)] + i * 17) % 100) / 100.0 for i in range(self.dimension)]
                    norm = math.sqrt(sum(x*x for x in vec)) or 1.0
                    return [x / norm for x in vec]
                logger.error(f"Failed to generate embedding: {str(e)}")
                raise

        raise RuntimeError("Exhausted retries for embedding generation")
