import os
import requests
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

API_BASE_URL = os.environ.get("API_BASE_URL", os.environ.get("API_URL", "http://localhost:8000")).rstrip("/")
API_URL = API_BASE_URL


def get_auth_headers() -> Dict[str, str]:
    """
    Centralized helper that retrieves authentication token from Streamlit session state
    or environment variables and formats the Authorization header for API Gateway / backend.
    """
    headers = {"Accept": "application/json"}
    
    # 1. Try Streamlit session state
    try:
        import streamlit as st
        token = st.session_state.get("auth_token") or st.session_state.get("id_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
            return headers
    except Exception:
        pass
        
    # 2. Try environment variable fallback
    env_token = os.environ.get("AUTH_TOKEN") or os.environ.get("JWT_TOKEN")
    if env_token:
        headers["Authorization"] = f"Bearer {env_token}"
        
    return headers


def _handle_request_error(e: requests.exceptions.RequestException, default_msg: str) -> str:
    """Format user-friendly error messages based on HTTP status code without leaking stack traces."""
    if e.response is not None:
        status = e.response.status_code
        if status == 401:
            return "Authentication required. Please log in with valid credentials."
        elif status == 403:
            return "Access denied. You do not have permission to view or perform this action."
        elif status == 404:
            return "Requested resource was not found."
        elif status == 409:
            return "A conflicting record or state already exists."
        elif status == 422:
            try:
                detail = e.response.json().get("detail")
                if isinstance(detail, list):
                    return f"Validation error: {detail[0].get('msg', 'Invalid input')}"
                return f"Validation error: {detail}"
            except Exception:
                return "Invalid input data format."
        elif status >= 500:
            return "Backend service temporarily unavailable. Please try again later."
            
        try:
            return e.response.json().get("detail", default_msg)
        except Exception:
            return default_msg
            
    return default_msg


def check_health() -> dict:
    try:
        response = requests.get(f"{API_BASE_URL}/health", headers=get_auth_headers(), timeout=3)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e), "status": "offline"}


def upload_document(filename: str, file_bytes: bytes, content_type: str, metadata: dict) -> dict:
    try:
        files = {"file": (filename, file_bytes, content_type)}
        data = {
            "owner": metadata.get("owner", "Team"),
            "category": metadata.get("category", "General"),
            "access_level": metadata.get("access_level", "team"),
            "version": metadata.get("version", "1.0")
        }
        headers = get_auth_headers()
        response = requests.post(f"{API_BASE_URL}/documents/upload", files=files, data=data, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error uploading document: {e}")
        return {"error": _handle_request_error(e, "Error uploading document")}


def get_document_status(document_id: str) -> dict:
    try:
        response = requests.get(f"{API_BASE_URL}/documents/{document_id}", headers=get_auth_headers(), timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching document status: {e}")
        return {"error": _handle_request_error(e, f"Unable to fetch document {document_id}")}


def list_documents() -> list:
    try:
        response = requests.get(f"{API_BASE_URL}/documents", headers=get_auth_headers(), timeout=5)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return data.get("documents", [])
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error listing documents: {e}")
        return []


def query_knowledge(query_text: str, access_levels: list = None) -> dict:
    try:
        payload: Dict[str, Any] = {"question": query_text}
        if access_levels:
            payload["access_levels"] = access_levels
        response = requests.post(
            f"{API_BASE_URL}/query",
            json=payload,
            headers=get_auth_headers(),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error querying knowledge: {e}")
        return {"error": _handle_request_error(e, "Backend server unreachable. Please check your connection.")}


def flag_content(
    document_id: str,
    reason: str,
    chunk_id: Optional[str] = None,
    flagged_by: str = "anonymous",
    details: Optional[str] = None,
    question: Optional[str] = None,
    answer: Optional[str] = None,
    source_filename: Optional[str] = None,
    supporting_passage: Optional[str] = None
) -> dict:
    try:
        payload = {
            "document_id": document_id,
            "reason": reason,
            "chunk_id": chunk_id,
            "flagged_by": flagged_by,
            "details": details,
            "question": question,
            "answer": answer,
            "source_filename": source_filename,
            "supporting_passage": supporting_passage
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        response = requests.post(f"{API_BASE_URL}/flags", json=payload, headers=get_auth_headers(), timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error flagging content: {e}")
        return {"error": _handle_request_error(e, "Failed to submit flag")}


def submit_flag(flag_data: dict) -> dict:
    """Compatibility wrapper for flag submission"""
    return flag_content(
        document_id=flag_data.get("document_id", "DOC-UNKNOWN"),
        reason=flag_data.get("reason", "Inaccurate information"),
        chunk_id=flag_data.get("chunk_id"),
        flagged_by=flag_data.get("flagged_by", "anonymous"),
        details=flag_data.get("details"),
        question=flag_data.get("question"),
        answer=flag_data.get("answer"),
        source_filename=flag_data.get("source_filename"),
        supporting_passage=flag_data.get("supporting_passage")
    )


def list_reviews(status: Optional[str] = None) -> list:
    try:
        params = {}
        if status and status.lower() not in ("all", ""):
            params["status"] = status
        response = requests.get(f"{API_BASE_URL}/reviews", params=params, headers=get_auth_headers(), timeout=5)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error listing reviews: {e}")
        return []


def resolve_review(flag_id: str, resolution: str, reviewer: str = "anonymous", notes: str = None) -> dict:
    try:
        payload = {"resolution": resolution, "reviewer": reviewer}
        if notes:
            payload["notes"] = notes
        response = requests.post(f"{API_BASE_URL}/reviews/{flag_id}/resolve", json=payload, headers=get_auth_headers(), timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error resolving review: {e}")
        return {"error": _handle_request_error(e, f"Unable to resolve review {flag_id}")}


def update_review_status(flag_id: str, new_status: str, reviewer: str = "Admin", notes: str = "") -> dict:
    """Compatibility wrapper for resolve_review"""
    return resolve_review(flag_id=flag_id, resolution=new_status, reviewer=reviewer, notes=notes)


def get_analytics() -> dict:
    try:
        response = requests.get(f"{API_BASE_URL}/analytics/overview", headers=get_auth_headers(), timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching analytics: {e}")
        return {"error": _handle_request_error(e, "Analytics service currently unavailable")}


# ---------------------------------------------------------------------------
# Phase 7 & 8: Auth / Freshness / Conflicts
# ---------------------------------------------------------------------------

def get_auth_me() -> dict:
    """Returns the current user's AuthContext from the backend."""
    try:
        response = requests.get(f"{API_BASE_URL}/auth/me", headers=get_auth_headers(), timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching auth context: {e}")
        return {"error": _handle_request_error(e, "Authentication context unavailable")}


def get_conflicts(document_id: str = None) -> list:
    """Returns conflict records, optionally filtered by document_id."""
    try:
        params = {"document_id": document_id} if document_id else {}
        response = requests.get(f"{API_BASE_URL}/conflicts", params=params, headers=get_auth_headers(), timeout=5)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching conflicts: {e}")
        return []


def get_document_freshness(document_id: str) -> dict:
    """Returns freshness metadata for a specific document."""
    try:
        response = requests.get(f"{API_BASE_URL}/documents/{document_id}/freshness", headers=get_auth_headers(), timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching freshness for {document_id}: {e}")
        return {"error": _handle_request_error(e, f"Freshness data unavailable for {document_id}")}

