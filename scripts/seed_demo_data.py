"""
Seed Demo Data Script — Team Knowledge Finder

Uploads synthetic demo documents from data/demo/ into the running backend API or AWS S3.
"""
import os
import sys
import glob
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "demo")


def seed_documents(api_url: str = API_BASE_URL):
    """Iterates over demo documents and uploads them via the backend API."""
    files = sorted(glob.glob(os.path.join(DEMO_DIR, "*.md")))
    if not files:
        logger.warning(f"No demo markdown files found in {DEMO_DIR}")
        return
        
    logger.info(f"Found {len(files)} demo documents to seed to {api_url}")
    
    headers = {}
    auth_token = os.environ.get("AUTH_TOKEN") or os.environ.get("JWT_TOKEN")
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
        
    for filepath in files:
        filename = os.path.basename(filepath)
        if filename == "questions.md":
            continue
            
        with open(filepath, "rb") as f:
            file_bytes = f.read()
            
        metadata = {
            "owner": "Atlas Platform",
            "category": "Documentation",
            "access_level": "team",
            "version": "1.0"
        }
        
        try:
            res = requests.post(
                f"{api_url}/documents/upload",
                files={"file": (filename, file_bytes, "text/markdown")},
                data=metadata,
                headers=headers,
                timeout=30
            )
            if res.status_code in (200, 201):
                logger.info(f"✅ Successfully uploaded {filename}")
            else:
                logger.warning(f"⚠️ Failed to upload {filename}: {res.status_code} - {res.text}")
        except Exception as e:
            logger.error(f"❌ Error uploading {filename}: {e}")


if __name__ == "__main__":
    seed_documents()
