from typing import List, Dict, Any
import re

class TextChunker:
    def __init__(self, chunk_size_words: int = 600, chunk_overlap_words: int = 80):
        self.chunk_size_words = chunk_size_words
        self.chunk_overlap_words = chunk_overlap_words

    def _normalize(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def chunk_document(self, document_id: str, filename: str, pages_content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        chunks = []
        chunk_index = 0
        
        for page_data in pages_content:
            page = page_data.get("page")
            text = self._normalize(page_data.get("text", ""))
            if not text:
                continue
                
            words = text.split()
            
            start = 0
            while start < len(words):
                end = min(start + self.chunk_size_words, len(words))
                chunk_words = words[start:end]
                chunk_text = " ".join(chunk_words)
                
                chunk_id = f"{document_id}-CHUNK-{chunk_index:04d}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "page_number": page,
                    "filename": filename
                })
                
                chunk_index += 1
                start += (self.chunk_size_words - self.chunk_overlap_words)
                
        return chunks
