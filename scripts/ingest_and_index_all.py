"""
Ingest & Index All Seeded Documents

Iterates through all uploaded documents in DynamoDB/local store,
extracts text chunks via Ingestion pipeline, marks status READY,
and indexes vectors via Indexing pipeline into OpenSearch/local store.
"""
import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.document_service import DocumentService
from backend.app.services.dynamodb_service import DynamoDBService
from backend.app.services.s3_service import S3Service
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.opensearch_service import OpenSearchService
from lambdas.ingestion.handler import process_s3_object
from lambdas.indexing.handler import lambda_handler as indexing_handler
from shared.constants.document_status import DocumentStatus
from shared.models.indexing import IndexedChunk

def main():
    doc_service = DocumentService()
    s3_service = S3Service()
    ddb_service = DynamoDBService()
    emb_service = EmbeddingService()
    os_service = OpenSearchService()
    
    docs = doc_service.list_documents()
    print(f"Discovered {len(docs)} documents in storage.")
    
    for doc in docs:
        print(f"\n--- Processing: {doc.filename} (v{doc.version}, {doc.document_id}) ---")
        if doc.status == DocumentStatus.SUPERSEDED:
            print(f"Skipping superseded document {doc.document_id}")
            continue
            
        s3_key = doc.s3_key or f"documents/raw/{doc.document_id}/{doc.filename}"
        
        # 1. Run Ingestion (extract text + chunk + mark READY)
        try:
            process_s3_object(s3_service.bucket_name, s3_key)
            print(f"✅ Ingested {doc.filename} -> Status: READY")
        except Exception as e:
            print(f"⚠️ Ingestion error for {doc.filename}: {e}")
            
        # 2. Run Indexing (load chunks + embed + index)
        try:
            chunks = s3_service.download_processed_chunks(doc.document_id, "text")
            if chunks:
                indexed_chunks = []
                for c in chunks:
                    text = c.get("text", "")
                    if not text.strip():
                        continue
                    emb = emb_service.embed_text(text)
                    indexed_chunks.append(IndexedChunk(
                        chunk_id=c.get("chunk_id", f"{doc.document_id}#c0"),
                        document_id=doc.document_id,
                        text=text,
                        embedding=emb,
                        chunk_index=c.get("chunk_index", 0),
                        page_number=c.get("page_number"),
                        filename=doc.filename,
                        owner=doc.owner,
                        category=doc.category,
                        access_level=doc.access_level.value if hasattr(doc.access_level, "value") else str(doc.access_level),
                        version=doc.version,
                        document_status=DocumentStatus.READY,
                        created_at=doc.created_at,
                        updated_at=doc.updated_at
                    ))
                if indexed_chunks:
                    os_service.bulk_index_chunks(indexed_chunks)
                    doc.indexing_status = "INDEXED"
                    ddb_service.update_document(doc)
                    print(f"✅ Indexed {len(indexed_chunks)} chunks into OpenSearch/Store")
        except Exception as e:
            print(f"⚠️ Indexing error for {doc.filename}: {e}")

    print("\nAll documents processed successfully!")

if __name__ == "__main__":
    main()
