import json
import urllib.parse
from typing import Dict, Any

from backend.app.core.logging import setup_logger
from backend.app.services.document_service import DocumentService
from backend.app.services.s3_service import S3Service
from backend.app.services.dynamodb_service import DynamoDBService
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.opensearch_service import OpenSearchService
from shared.models.indexing import IndexedChunk
from shared.constants.document_status import DocumentStatus

logger = setup_logger(__name__)

# Initialize services outside handler for reuse
s3_service = S3Service()
dynamodb_service = DynamoDBService()
document_service = DocumentService()
embedding_service = EmbeddingService()
opensearch_service = OpenSearchService()

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info("Indexing Lambda invoked")
    
    # Initialize index lazily (or ideally in deployment)
    try:
        opensearch_service.initialize_index()
    except Exception as e:
        logger.warning(f"Index initialization check failed: {e}")

    for record in event.get('Records', []):
        try:
            # 1. Parse Event
            bucket_name = record['s3']['bucket']['name']
            s3_key = urllib.parse.unquote_plus(record['s3']['object']['key'])
            
            logger.info(f"Processing event for s3://{bucket_name}/{s3_key}")
            
            # 2. Validate prefix (processed/text/{document_id}/chunks.json)
            if not s3_key.startswith("processed/text/") or not s3_key.endswith("chunks.json"):
                logger.warning(f"Ignoring irrelevant S3 key: {s3_key}")
                continue
                
            parts = s3_key.split('/')
            if len(parts) < 4:
                continue
            document_id = parts[2]
            
            # 3. Load Document Metadata
            doc = document_service.get_document(document_id)
            if not doc:
                logger.error(f"Document {document_id} not found in DynamoDB")
                continue
                
            if doc.status != DocumentStatus.READY:
                logger.warning(f"Document {document_id} is not READY (status: {doc.status}), skipping indexing")
                continue
                
            # 4. Mark Indexing Status
            doc.indexing_status = "INDEXING"
            dynamodb_service.update_document(doc)
            
            try:
                # 5. Load chunks from S3
                chunks_data = s3_service.download_processed_chunks(document_id, "text")
                if not chunks_data:
                    raise ValueError("No chunks found in S3")
                
                indexed_chunks = []
                for chunk_dict in chunks_data:
                    text = chunk_dict.get('text', '')
                    if not text.strip():
                        logger.warning(f"Skipping empty chunk {chunk_dict.get('chunk_id')}")
                        continue
                        
                    # 6. Generate Embedding
                    embedding = embedding_service.embed_text(text)
                    
                    # 7. Build IndexedChunk
                    indexed_chunk = IndexedChunk(
                        chunk_id=chunk_dict['chunk_id'],
                        document_id=doc.document_id,
                        text=text,
                        embedding=embedding,
                        chunk_index=chunk_dict['chunk_index'],
                        page_number=chunk_dict.get('page_number'),
                        filename=doc.filename,
                        owner=doc.owner,
                        category=doc.category,
                        access_level=doc.access_level.value if hasattr(doc.access_level, 'value') else str(doc.access_level),
                        version=doc.version,
                        document_status=doc.status.value if hasattr(doc.status, 'value') else str(doc.status),
                        created_at=doc.created_at,
                        updated_at=doc.updated_at
                    )
                    indexed_chunks.append(indexed_chunk)
                
                # 8. Bulk Index
                if not indexed_chunks:
                    raise ValueError("All chunks in the document were empty or invalid")
                    
                opensearch_service.bulk_index_chunks(indexed_chunks)
                
                # 9. Mark INDEXED
                doc.indexing_status = "INDEXED"
                doc.processing_error = None
                dynamodb_service.update_document(doc)
                logger.info(f"Successfully indexed document {document_id}")
                
            except Exception as e:
                # Handle Indexing Failure
                err_msg = str(e)
                logger.error(f"Failed to index document {document_id}: {err_msg}")
                doc.indexing_status = "INDEXING_FAILED"
                doc.processing_error = err_msg
                dynamodb_service.update_document(doc)

        except Exception as e:
            logger.error(f"Unexpected error processing record: {str(e)}")
            
    return {"statusCode": 200, "body": json.dumps("Indexing completed")}
