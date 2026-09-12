import boto3
import json
from typing import Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.core.exceptions import StorageError
from backend.app.core.logging import setup_logger

logger = setup_logger(__name__)

class S3Service:
    def __init__(self, bucket_name: str = settings.s3_bucket_name):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)
        
    def upload_file(self, file_bytes: bytes, object_key: str, metadata: Optional[Dict[str, str]] = None) -> str:
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_bytes,
                **extra_args
            )
            return object_key
        except Exception as e:
            logger.error(f"Failed to upload to S3: {str(e)}")
            raise StorageError(f"Failed to upload to S3: {str(e)}")

    def download_file(self, object_key: str) -> bytes:
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=object_key)
            return response['Body'].read()
        except Exception as e:
            logger.error(f"Failed to download from S3: {str(e)}")
            raise StorageError(f"Failed to download from S3: {str(e)}")
            
    def put_processed_text(self, document_id: str, data: Dict[str, Any]) -> str:
        object_key = f"processed/text/{document_id}/chunks.json"
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=json.dumps(data),
                ContentType="application/json"
            )
            return object_key
        except Exception as e:
            logger.error(f"Failed to save chunks to S3: {str(e)}")
            raise StorageError(f"Failed to save chunks to S3: {str(e)}")
