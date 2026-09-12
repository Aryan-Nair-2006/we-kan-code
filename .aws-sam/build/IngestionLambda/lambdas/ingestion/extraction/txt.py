from typing import List, Dict, Any
from lambdas.ingestion.extraction.base import DocumentExtractor

class TXTExtractor(DocumentExtractor):
    def extract(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        try:
            text = file_bytes.decode('utf-8').strip()
            if text:
                return [{"page": None, "text": text}]
            return []
        except Exception as e:
            raise Exception(f"Failed to parse TXT (ensure it is UTF-8): {str(e)}")
