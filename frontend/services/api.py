import os
import requests
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

API_BASE_URL = os.environ.get("API_BASE_URL", os.environ.get("API_URL", "http://localhost:8000")).rstrip("/")

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
        logger.error(f"Error getting document status: {e}")
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

def query_knowledge(query_text: str) -> dict:
    try:
        response = requests.post(
            f"{API_BASE_URL}/query",
            json={"question": query_text},
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

def get_analytics() -> dict:
    try:
        response = requests.get(f"{API_BASE_URL}/analytics/overview", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching analytics: {e}")
        return {"error": str(e)}

def submit_flag(flag_data: dict) -> dict:
    try:
        response = requests.post(
            f"{API_BASE_URL}/flags",
            json=flag_data,
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error submitting flag: {e}")
        return {"error": str(e)}

def list_reviews(status: str = "All") -> list:
    try:
        response = requests.get(f"{API_BASE_URL}/reviews", params={"status": status}, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error listing reviews: {e}")
        return []

def update_review_status(flag_id: str, new_status: str, reviewer: str = "Admin", notes: str = "") -> dict:
    try:
        response = requests.patch(
            f"{API_BASE_URL}/reviews/{flag_id}",
            json={"status": new_status, "reviewer": reviewer, "notes": notes},
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating review: {e}")
        return {"error": str(e)}
