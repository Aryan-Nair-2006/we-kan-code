import json
import os
from typing import Dict, Any

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "sample_documents")
DOCS_FILE = os.path.join(CACHE_DIR, "docs_store.json")
CHUNKS_FILE = os.path.join(CACHE_DIR, "chunks_store.json")
FLAGS_FILE = os.path.join(CACHE_DIR, "flags_store.json")
CONFLICTS_FILE = os.path.join(CACHE_DIR, "conflicts_store.json")

def load_json(filepath: str) -> Dict[str, Any]:
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_json(filepath: str, data: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception:
        pass
