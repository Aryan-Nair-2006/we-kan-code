import boto3
import json
import os
from typing import Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.core.exceptions import StorageError
from backend.app.core.logging import setup_logger

logger = setup_logger(__name__)

class S3Service:
    def __init__(self, bucket_name: str = settings.s3_bucket_name):
        self.bucket_name = bucket_name or "test-bucket"
        try:
            self.s3_client = boto3.client('s3', region_name=settings.aws_region or "us-east-1")
        except Exception as e:
            logger.warning(f"S3 client initialization warning: {e}")
            self.s3_client = None
        
    def upload_file(self, file_bytes: bytes, object_key: str, metadata: Optional[Dict[str, str]] = None) -> str:
        try:
            if self.s3_client and self.bucket_name:
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
            logger.warning(f"Failed to upload to AWS S3 (using local storage fallback): {str(e)}")
            
        # Local file fallback
        local_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "sample_documents", "uploaded_raw")
        os.makedirs(local_dir, exist_ok=True)
        filename = os.path.basename(object_key)
        local_path = os.path.join(local_dir, filename)
        with open(local_path, "wb") as f:
            f.write(file_bytes)
        return object_key

    def download_file(self, object_key: str) -> bytes:
        try:
            if self.s3_client and self.bucket_name:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=object_key)
                return response['Body'].read()
        except Exception as e:
            logger.warning(f"Failed to download from S3 (checking local storage fallback): {str(e)}")
            
        local_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "sample_documents", "uploaded_raw")
        filename = os.path.basename(object_key)
        local_path = os.path.join(local_dir, filename)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()
        raise StorageError(f"File {object_key} not found in S3 or local storage")
            
    def put_processed_text(self, document_id: str, data: Dict[str, Any]) -> str:
        object_key = f"processed/text/{document_id}/chunks.json"
        try:
            if self.s3_client and self.bucket_name:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    Body=json.dumps(data),
                    ContentType="application/json"
                )
                return object_key
        except Exception as e:
            logger.warning(f"Failed to save chunks to S3 (using local storage fallback): {str(e)}")
            
        local_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "sample_documents", "processed_text")
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, f"{document_id}_chunks.json")
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return object_key
