import json
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.services.s3_service import S3Service
from backend.app.services.dynamodb_service import DynamoDBService
from shared.constants.document_status import DocumentStatus
from lambdas.ingestion.extraction.pdf import PDFExtractor
from lambdas.ingestion.extraction.docx import DOCXExtractor
from lambdas.ingestion.extraction.txt import TXTExtractor
from lambdas.ingestion.extraction.xlsx import XLSXExtractor
from lambdas.ingestion.extraction.csv import CSVExtractor
from lambdas.ingestion.extraction.pptx import PPTXExtractor
from lambdas.ingestion.chunking.chunker import TextChunker
from backend.app.core.config import settings

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_service = S3Service()
dynamodb_service = DynamoDBService()
chunker = TextChunker(
    chunk_size_words=settings.chunk_size_words,
    chunk_overlap_words=settings.chunk_overlap_words
)

def get_extractor(file_type: str):
    file_type = file_type.lower()
    if file_type == 'pdf':
        return PDFExtractor()
    elif file_type == 'docx':
        return DOCXExtractor()
    elif file_type in ('txt', 'md'):
        return TXTExtractor()
    elif file_type == 'xlsx':
        return XLSXExtractor()
    elif file_type == 'csv':
        return CSVExtractor()
    elif file_type == 'pptx':
        return PPTXExtractor()
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

def process_s3_object(bucket: str, key: str):
    logger.info(f"Processing object: s3://{bucket}/{key}")
    
    # Example key: documents/raw/DOC-123/file.pdf
    parts = key.split('/')
    if len(parts) < 4 or parts[0] != 'documents' or parts[1] != 'raw':
        logger.info(f"Ignoring irrelevant S3 key: {key}")
        return
        
    document_id = parts[2]
    
    doc_meta = dynamodb_service.get_document(document_id)
    if not doc_meta:
        logger.error(f"Document {document_id} not found in DynamoDB.")
        return
        
    if doc_meta.status == DocumentStatus.READY:
        logger.info(f"Document {document_id} is already READY, skipping duplicate event.")
        return

    try:
        # Mark as processing
        doc_meta.status = DocumentStatus.PROCESSING
        dynamodb_service.update_document(doc_meta)
        
        # Download
        file_bytes = s3_service.download_file(key)
        
        # Extract
        extractor = get_extractor(doc_meta.file_type)
        pages_content = extractor.extract(file_bytes)
        
        if not pages_content:
            raise Exception("Document contains no extractable text.")
            
        # Chunk
        chunks = chunker.chunk_document(document_id, doc_meta.filename, pages_content)
        
        if not chunks:
            raise Exception("Document contains no extractable text after chunking.")
            
        # Store chunks
        s3_service.put_processed_text(document_id, {
            "document_id": document_id,
            "filename": doc_meta.filename,
            "chunks": chunks
        })
        
        # Mark ready
        doc_meta.status = DocumentStatus.READY
        doc_meta.chunk_count = len(chunks)
        doc_meta.processing_error = None
        dynamodb_service.update_document(doc_meta)
        
        logger.info(f"Successfully processed document {document_id} with {len(chunks)} chunks.")
        
    except Exception as e:
        logger.error(f"Failed to process document {document_id}: {str(e)}")
        doc_meta.status = DocumentStatus.FAILED
        doc_meta.processing_error = str(e)
        dynamodb_service.update_document(doc_meta)


import urllib.parse

def lambda_handler(event, context):
    """
    Ingestion Lambda Handler for Phase 2.
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    records = event.get('Records', [])
    for record in records:
        if 's3' in record:
            bucket = record['s3']['bucket']['name']
            raw_key = record['s3']['object']['key']
            key = urllib.parse.unquote_plus(raw_key)
            process_s3_object(bucket, key)
            
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Ingestion completed'})
    }
