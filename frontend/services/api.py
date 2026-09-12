import os
import requests
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

API_BASE_URL = os.environ.get("API_BASE_URL", os.environ.get("API_URL", "http://localhost:8000")).rstrip("/")
API_URL = API_BASE_URL


def check_health() -> dict:
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=3)
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
        response = requests.post(f"{API_BASE_URL}/documents/upload", files=files, data=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error uploading document: {e}")
        detail = "Server error"
        if e.response is not None:
            try:
                detail = e.response.json().get("detail", e.response.text)
            except Exception:
                detail = e.response.text
        return {"error": detail}


def get_document_status(document_id: str) -> dict:
    try:
        response = requests.get(f"{API_BASE_URL}/documents/{document_id}", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching document status: {e}")
        return {"error": str(e)}


def list_documents() -> list:
    try:
        response = requests.get(f"{API_BASE_URL}/documents", timeout=5)
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
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error querying knowledge: {e}")
        detail = "Backend server unreachable. Please check if FastAPI is running."
        if e.response is not None:
            try:
                detail = e.response.json().get("detail", e.response.text)
            except Exception:
                detail = e.response.text
        return {"error": detail}


def flag_content(document_id: str, reason: str, chunk_id: str = None, flagged_by: str = "anonymous") -> dict:
    try:
        payload = {"document_id": document_id, "reason": reason, "flagged_by": flagged_by}
        if chunk_id:
            payload["chunk_id"] = chunk_id
        response = requests.post(f"{API_BASE_URL}/flags", json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error flagging content: {e}")
        return {"error": str(e)}


def submit_flag(flag_data: dict) -> dict:
    """Compatibility wrapper for flag submission"""
    doc_id = flag_data.get("document_id", "DOC-UNKNOWN")
    reason = flag_data.get("reason", "Inaccurate information")
    chunk_id = flag_data.get("chunk_id")
    flagged_by = flag_data.get("flagged_by", "anonymous")
    return flag_content(document_id=doc_id, reason=reason, chunk_id=chunk_id, flagged_by=flagged_by)


def list_reviews(status: Optional[str] = None) -> list:
    try:
        params = {}
        if status and status.lower() not in ("all", ""):
            params["status"] = status
        response = requests.get(f"{API_BASE_URL}/reviews", params=params, timeout=5)
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
        response = requests.post(f"{API_BASE_URL}/reviews/{flag_id}/resolve", json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error resolving review: {e}")
        return {"error": str(e)}


def update_review_status(flag_id: str, new_status: str, reviewer: str = "Admin", notes: str = "") -> dict:
    """Compatibility wrapper for resolve_review"""
    return resolve_review(flag_id=flag_id, resolution=new_status, reviewer=reviewer, notes=notes)


def get_analytics() -> dict:
    try:
        response = requests.get(f"{API_BASE_URL}/analytics/overview", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching analytics: {e}")
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Phase 7: Auth / Freshness / Conflicts
# ---------------------------------------------------------------------------

def get_auth_me() -> dict:
    """Returns the current user's AuthContext from the backend."""
    try:
        response = requests.get(f"{API_BASE_URL}/auth/me", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching auth context: {e}")
        return {"error": str(e)}


def get_conflicts(document_id: str = None) -> list:
    """Returns conflict records, optionally filtered by document_id."""
    try:
        params = {"document_id": document_id} if document_id else {}
        response = requests.get(f"{API_BASE_URL}/conflicts", params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching conflicts: {e}")
        return []


def get_document_freshness(document_id: str) -> dict:
    """Returns freshness metadata for a specific document."""
    try:
        response = requests.get(f"{API_BASE_URL}/documents/{document_id}/freshness", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching freshness for {document_id}: {e}")
        return {"error": str(e)}
