import io
import docx
from typing import List, Dict, Any
from lambdas.ingestion.extraction.base import DocumentExtractor

class DOCXExtractor(DocumentExtractor):
    def extract(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        try:
            docx_file = io.BytesIO(file_bytes)
            doc = docx.Document(docx_file)
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text.strip())
            
            if full_text:
                return [{"page": None, "text": "\n\n".join(full_text)}]
            return []
        except Exception as e:
            raise Exception(f"Failed to parse DOCX: {str(e)}")
