from lambdas.ingestion.extraction.txt import TXTExtractor
from lambdas.ingestion.chunking.chunker import TextChunker
import pytest

def test_txt_extractor():
    extractor = TXTExtractor()
    result = extractor.extract(b"Hello world\nThis is a test.")
    assert len(result) == 1
    assert result[0]["page"] is None
    assert result[0]["text"] == "Hello world\nThis is a test."

def test_txt_extractor_empty():
    extractor = TXTExtractor()
    result = extractor.extract(b"   \n  ")
    assert len(result) == 0

def test_chunker_basic():
    chunker = TextChunker(chunk_size_words=5, chunk_overlap_words=2)
    pages = [{"page": 1, "text": "This is a simple test document for chunking logic."}]
    # Words: This (0) is (1) a (2) simple (3) test (4) document (5) for (6) chunking (7) logic. (8)
    # Expected chunks:
    # 1: This is a simple test
    # 2: simple test document for chunking
    # 3: for chunking logic.
    chunks = chunker.chunk_document("DOC-1", "test.txt", pages)
    
    assert len(chunks) == 3
    assert chunks[0]["text"] == "This is a simple test"
    assert chunks[0]["page_number"] == 1
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["chunk_id"] == "DOC-1-CHUNK-0000"
    
    assert chunks[1]["text"] == "simple test document for chunking"
    assert chunks[1]["page_number"] == 1
    assert chunks[1]["chunk_index"] == 1
    
    assert chunks[2]["text"] == "for chunking logic."
    assert chunks[2]["page_number"] == 1
    assert chunks[2]["chunk_index"] == 2
