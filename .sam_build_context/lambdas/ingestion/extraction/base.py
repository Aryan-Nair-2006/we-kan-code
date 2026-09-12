from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class DocumentExtractor(ABC):
    @abstractmethod
    def extract(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Extract text from file bytes.
        Returns a list of dicts, e.g., [{"page": 1, "text": "..."}]
        """
        pass
