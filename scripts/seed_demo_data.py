"""
Seed Demo Data Script — Team Knowledge Finder

Uploads synthetic demo documents from data/demo/ into the running backend API or AWS S3
with tailored metadata for RBAC access levels, document categories, and versioning.
Supports `--dry-run` for offline validation.
"""
import os
import sys
import glob
import logging
import argparse
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "demo")

# Explicit metadata mapping tailored for each synthetic document to exercise RBAC, versioning, and conflicts
DOC_METADATA = {
    "01_project_architecture_overview.md": {
        "upload_filename": "01_project_architecture_overview.md",
        "owner": "Architecture Team",
        "category": "Architecture",
        "access_level": "team",
        "version": "2.0"
    },
    "02_api_specification_v1_legacy.md": {
        "upload_filename": "api_specification.md",  # Shared logical filename to test v1 -> v2 superseding
        "owner": "Backend Team",
        "category": "API",
        "access_level": "team",
        "version": "1.0"
    },
    "02_api_specification_v2.md": {
        "upload_filename": "api_specification.md",  # Uploaded second to supersede v1.0
        "owner": "Backend Team",
        "category": "API",
        "access_level": "team",
        "version": "2.0"
    },
    "03_database_data_model.md": {
        "upload_filename": "03_database_data_model.md",
        "owner": "Data Team",
        "category": "Database",
        "access_level": "developer",
        "version": "1.5"
    },
    "04_deployment_runbook.md": {
        "upload_filename": "04_deployment_runbook.md",
        "owner": "DevOps Team",
        "category": "Operations",
        "access_level": "developer",
        "version": "1.2"
    },
    "05_security_access_policy.md": {
        "upload_filename": "05_security_access_policy.md",
        "owner": "Security Team",
        "category": "Security",
        "access_level": "admin",
        "version": "2.1"
    },
    "06_product_requirements_doc.md": {
        "upload_filename": "06_product_requirements_doc.md",
        "owner": "Product Team",
        "category": "Product",
        "access_level": "team",
        "version": "1.8"
    },
    "07_incident_report_inc_402.md": {
        "upload_filename": "07_incident_report_inc_402.md",
        "owner": "SRE Team",
        "category": "Incidents",
        "access_level": "team",
        "version": "1.0"
    },
    "08_engineering_decision_record_edr09.md": {
        "upload_filename": "08_engineering_decision_record_edr09.md",
        "owner": "AI Team",
        "category": "Architecture",
        "access_level": "developer",
        "version": "1.0"
    },
    "09_team_onboarding_guide.md": {
        "upload_filename": "09_team_onboarding_guide.md",
        "owner": "Developer Experience",
        "category": "Onboarding",
        "access_level": "public",
        "version": "1.3"
    },
    "10_project_faq.md": {
        "upload_filename": "10_project_faq.md",
        "owner": "Support Team",
        "category": "FAQ",
        "access_level": "public",
        "version": "1.1"
    },
    "11_emergency_deployment_override.md": {
        "upload_filename": "11_emergency_deployment_override.md",
        "owner": "SRE Incident Team",
        "category": "Operations",
        "access_level": "developer",
        "version": "1.0"
    }
}


def seed_documents(api_url: str = API_BASE_URL, dry_run: bool = False):
    """Iterates over demo documents and uploads them via the backend API with specific metadata."""
    ordered_files = [
        "01_project_architecture_overview.md",
        "02_api_specification_v1_legacy.md",
        "02_api_specification_v2.md",
        "03_database_data_model.md",
        "04_deployment_runbook.md",
        "05_security_access_policy.md",
        "06_product_requirements_doc.md",
        "07_incident_report_inc_402.md",
        "08_engineering_decision_record_edr09.md",
        "09_team_onboarding_guide.md",
        "10_project_faq.md",
        "11_emergency_deployment_override.md"
    ]
    
    headers = {}
    auth_token = os.environ.get("AUTH_TOKEN") or os.environ.get("JWT_TOKEN")
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
        
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Starting seed of {len(ordered_files)} demo documents to {api_url}")
    
    success_count = 0
    for filename in ordered_files:
        filepath = os.path.join(DEMO_DIR, filename)
        if not os.path.exists(filepath):
            logger.warning(f"File {filepath} not found, skipping...")
            continue
            
        meta = DOC_METADATA.get(filename, {
            "upload_filename": filename,
            "owner": "Atlas Team",
            "category": "General",
            "access_level": "team",
            "version": "1.0"
        })
        
        upload_name = meta.get("upload_filename", filename)
        
        with open(filepath, "rb") as f:
            file_bytes = f.read()
            
        payload_data = {
            "owner": meta["owner"],
            "category": meta["category"],
            "access_level": meta["access_level"],
            "version": meta["version"]
        }
        
        if dry_run:
            logger.info(f"[DRY RUN] Would upload '{filename}' as '{upload_name}' ({len(file_bytes)} bytes, v{meta['version']}, {meta['access_level']}) to {api_url}/documents/upload")
            success_count += 1
            continue
            
        try:
            res = requests.post(
                f"{api_url}/documents/upload",
                files={"file": (upload_name, file_bytes, "text/markdown")},
                data=payload_data,
                headers=headers,
                timeout=120
            )
            if res.status_code in (200, 201):
                doc_res = res.json()
                logger.info(f"✅ Uploaded '{filename}' as '{upload_name}' (v{meta['version']}, {meta['access_level']}) -> ID: {doc_res.get('document_id', 'OK')}")
                success_count += 1
            else:
                logger.warning(f"⚠️ Failed to upload {filename}: {res.status_code} - {res.text}")
        except Exception as e:
            logger.error(f"❌ Error uploading {filename}: {e}")

    logger.info(f"Summary: {success_count}/{len(ordered_files)} documents processed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed synthetic demo documents into Team Knowledge Finder")
    parser.add_argument("--api-url", default=API_BASE_URL, help="Backend API base URL")
    parser.add_argument("--dry-run", action="store_true", help="Validate document discovery and metadata without uploading")
    args = parser.parse_args()
    
    seed_documents(api_url=args.api_url, dry_run=args.dry_run)
