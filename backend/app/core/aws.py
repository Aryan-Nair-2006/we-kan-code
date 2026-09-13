import os
from typing import Optional
import boto3
from backend.app.core.config import settings
from backend.app.core.logging import setup_logger

logger = setup_logger(__name__)

_has_credentials: Optional[bool] = None

def has_valid_aws_credentials() -> bool:
    """
    Checks once whether valid AWS credentials exist.
    Caches the result so subsequent calls take < 1 microsecond.
    """
    global _has_credentials
    if _has_credentials is not None:
        return _has_credentials
        
    if settings.environment == "local":
        # In local development mode, if explicit fake/dummy or missing keys, fast-track to False
        ak = os.environ.get("AWS_ACCESS_KEY_ID", "").strip()
        sk = os.environ.get("AWS_SECRET_ACCESS_KEY", "").strip()
        if not ak or not sk or ak.startswith("dummy") or ak.startswith("fake"):
            _has_credentials = False
            return False
            
    try:
        session = boto3.Session()
        creds = session.get_credentials()
        _has_credentials = creds is not None
    except Exception:
        _has_credentials = False
        
    return _has_credentials

def get_boto3_client(service_name: str, region_name: Optional[str] = None):
    if not has_valid_aws_credentials():
        return None
    try:
        return boto3.client(service_name, region_name=region_name or settings.aws_region)
    except Exception as e:
        logger.warning(f"Failed to create boto3 client for {service_name}: {e}")
        return None

def get_boto3_resource(service_name: str, region_name: Optional[str] = None):
    if not has_valid_aws_credentials():
        return None
    try:
        return boto3.resource(service_name, region_name=region_name or settings.aws_region)
    except Exception as e:
        logger.warning(f"Failed to create boto3 resource for {service_name}: {e}")
        return None
