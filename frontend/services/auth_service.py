"""
Authentication Service — Phase 8

Provides Cognito User Pool authentication for Streamlit frontend and session state token management.
Supports both Cognito User Pool (USER_PASSWORD_AUTH) and local development mode.
"""
import os
import json
import base64
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Environment Configuration
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")


def _decode_jwt_payload(token: str) -> Dict[str, Any]:
    """Decodes JWT payload without cryptographic verification for client-side display only."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload_b64 = parts[1]
        # Pad base64 if needed
        padding = 4 - (len(payload_b64) % 4)
        if padding != 4:
            payload_b64 += "=" * padding
        decoded = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
        return json.loads(decoded)
    except Exception as e:
        logger.warning(f"Failed to parse JWT payload: {e}")
        return {}


def login_with_cognito(
    username: str,
    password: str,
    client_id: Optional[str] = None,
    user_pool_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Authenticates a user against Amazon Cognito using USER_PASSWORD_AUTH flow.
    Returns dict with tokens and user details on success, or error message on failure.
    """
    client_id = client_id or COGNITO_CLIENT_ID or os.environ.get("COGNITO_CLIENT_ID", "")
    region = region or AWS_REGION or os.environ.get("AWS_REGION", "ap-south-1")
    
    if not client_id:
        return {
            "success": False,
            "error": "Cognito Client ID not configured. Set COGNITO_CLIENT_ID environment variable."
        }
        
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        cognito = boto3.client("cognito-idp", region_name=region)
        response = cognito.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password
            }
        )
        
        auth_result = response.get("AuthenticationResult", {})
        id_token = auth_result.get("IdToken", "")
        access_token = auth_result.get("AccessToken", "")
        refresh_token = auth_result.get("RefreshToken", "")
        
        # Decode claims from ID token (or Access token) for UI display
        claims = _decode_jwt_payload(id_token) if id_token else _decode_jwt_payload(access_token)
        user_role = claims.get("custom:role") or (claims.get("cognito:groups", ["public"])[0] if claims.get("cognito:groups") else "public")
        
        return {
            "success": True,
            "id_token": id_token,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "username": claims.get("cognito:username") or username,
            "email": claims.get("email", username),
            "role": user_role,
            "expires_in": auth_result.get("ExpiresIn", 3600)
        }
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "AuthError")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Cognito authentication failed: {error_code} - {error_msg}")
        
        if error_code in ("NotAuthorizedException", "UserNotFoundException"):
            return {"success": False, "error": "Invalid username or password"}
        elif error_code == "PasswordResetRequiredException":
            return {"success": False, "error": "Password reset required"}
        elif error_code == "UserNotConfirmedException":
            return {"success": False, "error": "User account is not confirmed"}
        return {"success": False, "error": f"Authentication failed: {error_msg}"}
        
    except Exception as e:
        logger.error(f"Unexpected error during Cognito authentication: {e}")
        return {"success": False, "error": f"Connection error: {str(e)}"}


def login_local(username: str, role: str = "team") -> Dict[str, Any]:
    """Helper for local offline development authentication."""
    return {
        "success": True,
        "id_token": f"mock-token-for-{username}-{role}",
        "access_token": f"mock-token-for-{username}-{role}",
        "username": username,
        "email": f"{username}@local.dev",
        "role": role,
        "expires_in": 86400
    }
