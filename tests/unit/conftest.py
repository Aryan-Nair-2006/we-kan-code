# tests/unit/conftest.py
"""
Conftest for unit tests — patches boto3 and AWS4Auth at import time.

S3Service, DynamoDBService, OpenSearchService etc. all instantiate AWS clients
in __init__. Without real AWS env vars this fails during test collection.

We patch at module level (before collection) using start()/stop().
"""
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Patch at module level — must run before any test module is imported.
# ---------------------------------------------------------------------------

_mock_client = MagicMock()
_mock_resource = MagicMock()
_mock_table = MagicMock()
_mock_resource.Table.return_value = _mock_table

# Credentials mock: secret_key must be bytes for AWS4Auth HMAC
_mock_credentials = MagicMock()
_mock_credentials.access_key = "FAKEKEYID"
_mock_credentials.secret_key = "FAKESECRETKEY"
_mock_credentials.token = None

_mock_session_instance = MagicMock()
_mock_session_instance.get_credentials.return_value = _mock_credentials

_patcher_boto3_client = patch("boto3.client", return_value=_mock_client)
_patcher_boto3_resource = patch("boto3.resource", return_value=_mock_resource)
_patcher_boto3_session = patch("boto3.Session", return_value=_mock_session_instance)

_patcher_boto3_client.start()
_patcher_boto3_resource.start()
_patcher_boto3_session.start()
