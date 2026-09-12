import io
from pypdf import PdfReader
from typing import List, Dict, Any
from lambdas.ingestion.extraction.base import DocumentExtractor

class PDFExtractor(DocumentExtractor):
    def extract(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        pages_content = []
        try:
            pdf_file = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_file)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages_content.append({"page": i + 1, "text": text.strip()})
        except Exception as e:
            raise Exception(f"Failed to parse PDF: {str(e)}")
            
        return pages_content
